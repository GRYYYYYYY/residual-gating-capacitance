"""Official AttentionCap backbone/head, adapted FEM component supervision.
The added external-boundary token closes the Laplacian's ground node. No full
matrix labels or extra target observations are used. A geometry/material adapter
is necessary: the original homogeneous conductor inputs do not encode this FEM.
"""
import argparse,copy,importlib.util,time,gzip,collections
from common import *
import torch
from torch import nn
from pdkcap.metrics import record,summarize
from learning import tensor
from evaluate import trajectory
SRC=ROOT/'.cache/AttentionCap/src/model.py'
spec=importlib.util.spec_from_file_location('official_attentioncap',SRC);mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
DEST=ROOT/'results/dac_characterization_20261114/attention'
# Entire geometry pools are declared transductive inputs; no grid contains labels.
GRIDS={}
for gen in ('reference_design_v2','round2_design_v2','round3_design_v1'):
    for g in json.loads((ROOT/f'runs/{gen}/grid.json').read_text()):
        m=g['spec']['metadata'];GRIDS[(g['reference_id'],(m['width_um'],m['distance_um'],m['lateral_spacing_um']))]=g
MAX_MATERIALS=max(len(c['materials']) for gen in ('reference_design_v2','round2_design_v2','round3_design_v1') for c in json.loads((ROOT/f'runs/{gen}/contracts.json').read_text()))
DIM=4+3*MAX_MATERIALS+2

def features(t):
    xs=[];projs=[]
    for coord in t['coordinates']:
        g=GRIDS[(t['table_id'],tuple(coord))];s=g['spec'];meta=s['metadata'];rect=s['rectangles_override'];n=len(rect)
        # Ground node is an explicit global boundary token (not a fake label).
        x=np.zeros((n+1,DIM),dtype='float32');x[:n,:4]=rect
        materials=t['materials'];flat=np.array([[r['bottom'],r['top'],r['er']/10.] for r in materials]).ravel()
        if len(flat)>3*MAX_MATERIALS:raise ValueError('material padding insufficient')
        x[:,4:4+len(flat)]=flat;x[-1,-2]=1.;x[:,-1]=s['extent']
        projection=np.zeros((3,n+1),dtype='float32');projection[0,meta['lateral_indices']]=1;projection[1,meta['grounded_indices']]=1;projection[1,-1]=1;projection[2,meta['diagonal_indices']]=1
        assert meta['target_index']==0
        xs.append(x);projs.append(projection)
    assert len({a.shape for a in xs})==1
    return tensor(np.array(xs)),tensor(np.array(projs))
def build():return mod.GPT(mod.GPTConfig(n_layer=2,n_head=4,n_embd=64,input_dim=DIM,use_transformer=True,attention_type='symmetric',head_activation='exp'))
def forward(model,x,pr):
    matrix,_=model(x);return torch.einsum('bn,bkn->bk',-matrix[:,0,:],pr)
def projected(model,sc,t,o,v,steps):
    x,pr=features(t);ys=np.asarray(sc['targets'][t['family']]);unit=float(np.mean(ys));target=tensor(v/ys)
    if steps:
        model=copy.deepcopy(model);opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=1e-4)
        for _ in range(steps):
            opt.zero_grad();pred=forward(model,x[o],pr[o])*tensor(unit/ys);loss=nn.functional.huber_loss(pred,target);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
    with torch.inference_mode():return forward(model,x,pr).numpy()*unit

def fit(setting,lr,seed):
    d=DEST/f'{setting}_lr{lr:g}_s{seed}';d.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(seed);rng=np.random.default_rng(seed)
    _,sc=full(setting);ts=tables(setting,'train');data=[]
    for t in ts:
        x,pr=features(t);ys=np.asarray(sc['targets'][t['family']]);data.append((x,pr,tensor(np.asarray(t['labels'])/ys),tensor(float(np.mean(ys))/ys)))
    model=build();opt=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=1e-4)
    write(d/'FROZEN.json',dict(source=str(SRC),source_sha256=sha(SRC),adapter_sha256=sha(__file__),lr=lr,seed=seed,steps=3000,training_ids=[t['table_id'] for t in ts],extra_supervision=False,dim=DIM,projection='same three FEM components; explicit external-boundary token'))
    start=time.perf_counter();cpu=time.process_time()
    for step in range(3000):
        i=int(rng.integers(len(data)));x,pr,y,scale=data[i];idx=rng.choice(len(x),min(32,len(x)),replace=False)
        opt.zero_grad();pred=forward(model,x[idx],pr[idx])*scale;loss=nn.functional.huber_loss(pred,y[idx]);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
    torch.save(dict(state_dict=model.state_dict(),scales=sc),d/'checkpoint.pt');model.eval()
    write(d/'COMPLETED.json',dict(steps=3000,wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,last_loss=float(loss.detach()),checkpoint_sha256=sha(d/'checkpoint.pt')))
    return model,sc

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--setting',required=True,choices=['reference','to_asap7']);a=ap.parse_args();s=a.setting
    DEST.mkdir(parents=True,exist_ok=True);choices=[];validation=[]
    for lr in (.001,.0003):
        model,sc=fit(s,lr,0)
        for steps in (0,50,200):
            rs=[]
            for t in tables(s,'val'):
                _,q,snaps=trajectory(t,11,'farthest')
                for o,v,_,_ in snaps:
                    p=projected(model,sc,public_input(t),o,v,steps);rs.append(record(t,np.asarray(t['labels'])[q],p[q],budget=len(o),lr=lr,adapt_steps=steps))
            score=summarize(rs)['nrmse'];choices.append(dict(lr=lr,adapt_steps=steps,score=score));validation+=rs
    best=min(choices,key=lambda a:(a['score'],a['adapt_steps'],a['lr']));write(DEST/f'{s}_selection.json',best|dict(candidates=choices))
    members=[]
    for seed in (0,1,2):
        if seed:
            model,sc=fit(s,best['lr'],seed)
        else:
            state=torch.load(DEST/f'{s}_lr{best["lr"]:g}_s0/checkpoint.pt',map_location='cpu',weights_only=True);model=build();model.load_state_dict(state['state_dict']);sc=state['scales'];model.eval()
        members.append(model)
    with gzip.open(DEST/f'{s}_validation.jsonl.gz','xt') as f:
        for r in validation:f.write(json.dumps(r)+'\n')
    # Confirmation only after selecting LR/adaptation on source validation.
    out=DEST/f'{s}_confirmation';out.mkdir(exist_ok=False);rows=[]
    from evaluate import costs
    ts=tables(s,'confirmation');cost=costs(s,ts)
    with gzip.open(out/'records.jsonl.gz','xt') as f:
        for t in ts:
            for seed in (11,29,47):
                c,q,snaps=trajectory(t,seed,'farthest')
                for o,v,_,_ in snaps:
                    for name,steps in [('attentioncap_zero',0),('attentioncap_adapted',best['adapt_steps'])]:
                        start=time.perf_counter();pred=np.mean([projected(m,sc,public_input(t),o,v,steps) for m in members],0);pred[o]=v
                        r=record(t,np.asarray(t['labels'])[q],pred[q],setting=s,method=name,budget=len(o),data_seed=seed,status='ok',query_indices=q.tolist(),support_indices=o.tolist(),candidate_indices=c.tolist(),prediction=pred.tolist(),strategy='farthest',adapt_steps=steps,unique_reference_queries=len(o) if steps else 0,solver_cpu_seconds_fine=float(cost[t['table_id']]['fine'][o].sum()) if steps else 0.,prediction_and_adaptation_wall_seconds=time.perf_counter()-start)
                        f.write(json.dumps(r)+'\n');rows.append(r)
    write(out/'COMPLETED.json',dict(records=len(rows),failed=0,selection=best,upstream_model_sha256=sha(SRC),adapter_sha256=sha(__file__)))
    print(s,best,flush=True)
if __name__=='__main__':main()
