"""Bounded CNP/direct-regression controls. No query-label target adaptation."""
import argparse,copy,json,time
import torch
from torch import nn
import numpy as np
from common import *
from unified.basis import context_vector
from pdkcap.metrics import record,summarize
PLAN=json.loads((HERE/'EXPERIMENT_PLAN.yaml').read_text())
DEST=ROOT/'results/dac_characterization_20261114/learning'

def feature(t,sc):
    x=np.asarray(t['coordinates']);c=context_vector(t)
    return np.c_[np.log1p(x/np.asarray(sc['coordinates'])),np.tile(c,(len(x),1))].astype('float32')
def tensor(a):return torch.as_tensor(a,dtype=torch.float32)
class Net(nn.Module):
    def __init__(self,kind,dim,k):
        super().__init__();self.kind=kind
        if kind=='cnp':self.context=nn.Sequential(nn.Linear(dim+k,64),nn.ReLU(),nn.Linear(64,64),nn.ReLU())
        self.decode=nn.Sequential(nn.Linear(dim+(64 if kind=='cnp' else 0),64),nn.ReLU(),nn.Linear(64,64),nn.ReLU(),nn.Linear(64,k))
    def forward(self,x,o=None,y=None):
        if self.kind=='cnp':
            if len(o)==0:raise ValueError('CNP needs observations')
            z=self.context(torch.cat([x[o],y],-1)).mean(0).expand(len(x),-1)
            x=torch.cat([x,z],-1)
        return self.decode(x)

def fit(setting,kind,lr,seed,steps=3000):
    d=DEST/f'{setting}_{kind}_lr{lr:g}_s{seed}';d.mkdir(parents=True,exist_ok=False)
    _,sc=full(setting);ts=tables(setting,'train');torch.manual_seed(seed);rng=np.random.default_rng(seed);torch.set_num_threads(1)
    model=Net(kind,feature(ts[0],sc).shape[1],len(ts[0]['target_names']))
    opt=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=1e-4)
    cached=[(tensor(feature(t,sc)),tensor(np.asarray(t['labels'])/np.asarray(sc['targets'][t['family']]))) for t in ts]
    groups={fam:[i for i,t in enumerate(ts) if t['family']==fam] for fam in sorted({t['family'] for t in ts})}
    write(d/'FROZEN.json',dict(setting=setting,kind=kind,learning_rate=lr,seed=seed,steps=steps,training_ids=[t['table_id'] for t in ts],scales=sc,code_sha256=sha(__file__),plan_sha256=sha(HERE/'EXPERIMENT_PLAN.yaml')))
    start=time.perf_counter();cpu=time.process_time()
    for step in range(steps):
        opt.zero_grad();loss=0
        for fam,ids in groups.items():
            i=int(rng.choice(ids));x,y=cached[i];n=len(x)
            order=rng.permutation(n);b=int(rng.choice([2,4,8,16,32,64]));b=min(b,n-1);o=order[:b];q=order[b:]
            pred=model(x,o,y[o]);loss=loss+torch.nn.functional.huber_loss(pred[q],y[q])/len(groups)
        loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
    model.eval();torch.save(dict(state_dict=model.state_dict(),kind=kind,dim=feature(ts[0],sc).shape[1],k=len(ts[0]['target_names']),scales=sc),d/'checkpoint.pt')
    write(d/'COMPLETED.json',dict(steps=steps,wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,checkpoint_sha256=sha(d/'checkpoint.pt'),last_loss=float(loss.detach())))
    return model,sc

def load(setting,kind,lr,seed):
    d=DEST/f'{setting}_{kind}_lr{lr:g}_s{seed}';state=torch.load(d/'checkpoint.pt',map_location='cpu',weights_only=True)
    assert sha(d/'checkpoint.pt')==json.loads((d/'COMPLETED.json').read_text())['checkpoint_sha256']
    m=Net(kind,state['dim'],state['k']);m.load_state_dict(state['state_dict']);m.eval();return m,state['scales']

def prediction(model,sc,t,o,v,adapt=0):
    x=tensor(feature(t,sc));ys=np.asarray(sc['targets'][t['family']]);y=tensor(v/ys)
    if adapt:
        model=copy.deepcopy(model);opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=1e-4)
        for _ in range(adapt):
            opt.zero_grad();loss=nn.functional.huber_loss(model(x,o,y)[o],y);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
    with torch.inference_mode():p=model(x,o,y).numpy()*ys
    return np.maximum(p,0)

class Learned:
    def __init__(self,setting):
        self.setting=setting;self.sel=json.loads((DEST/f'{setting}_selection.json').read_text());self.models={}
        for kind in ('mlp','cnp'):self.models[kind]=[load(setting,kind,self.sel[kind]['lr'],s) for s in (0,1,2)]
    def predict(self,name,t,o,v,adapt_steps=50):
        kind='cnp' if name=='cnp' else 'mlp'
        if name not in ('cnp','mlp_zero','mlp_adapt'):raise ValueError(name)
        n=self.sel['mlp']['adapt_steps'] if name=='mlp_adapt' else 0
        return np.mean([prediction(m,sc,t,o,v,n) for m,sc in self.models[kind]],0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--setting',required=True);ap.add_argument('--pilot',action='store_true');a=ap.parse_args();s=a.setting
    from evaluate import trajectory
    DEST.mkdir(parents=True,exist_ok=True);chosen={};raw=[]
    for kind in ('mlp','cnp'):
        choices=[]
        for lr in (.001,.0003):
            model,sc=fit(s,kind,lr,0,steps=100 if a.pilot else 3000)
            if a.pilot:continue
            for adapt in ([0,50,200] if kind=='mlp' else [0]):
                rs=[]
                for t in tables(s,'val'):
                    if len(t['coordinates'])<4:continue
                    c,q,snaps=trajectory(t,11,'farthest')
                    for o,v,_,_ in snaps:
                        p=prediction(model,sc,public_input(t),o,v,adapt)
                        r=record(t,np.asarray(t['labels'])[q],p[q],budget=len(o),lr=lr,adapt_steps=adapt,kind=kind);rs.append(r)
                score=summarize(rs)['nrmse'];choices.append(dict(lr=lr,adapt_steps=adapt,score=score));raw+=rs
        if a.pilot:continue
        best=min(choices,key=lambda c:(c['score'],c['adapt_steps'],c['lr']));chosen[kind]=best|dict(candidates=choices)
        for seed in (1,2):fit(s,kind,best['lr'],seed)
    if not a.pilot:
        write(DEST/f'{s}_selection.json',chosen)
        with __import__('gzip').open(DEST/f'{s}_validation.jsonl.gz','xt') as f:
            for r in raw:f.write(json.dumps(r)+'\n')
    print(s,chosen,flush=True)
if __name__=='__main__':main()
