"""Same-S/Q CPU timing. Canonical verification precedes any batch sweep.
Each block visits every requested query once. Setup is charged separately.
"""
from common_runtime import *
import copy,importlib.util,collections,argparse
import numpy as np,torch
from common import public_input
from evaluate import Predictors
from learning import feature,tensor
from unified.queries import query_table
from unified.episodes import encode,stack
import unified.episodes as episodes
from unified.basis import CLASSICAL

METHODS=['anchor','cmi','affine','gp','residual','binary','full','mlp_adapt','cnp']
class Engine:
    def __init__(self,kind):
        self.kind=kind;self.setting='public' if kind=='native' else 'to_asap7'
        t=stamp();self.p=Predictors(self.setting,read(R/f'experiments/dac_characterization_20261114/selected_{self.setting}.json'))
        self.load=elapsed(t);self.cache={};self.prep=[];self.att=None
        if kind=='fem':
            import attention
            self.att=attention;self.att_members=[];sel=read(attention.DEST/'to_asap7_selection.json');self.att_steps=sel['adapt_steps']
            t=stamp()
            for seed in range(3):
                path=attention.DEST/f'to_asap7_lr{sel["lr"]:g}_s{seed}/checkpoint.pt'
                state=torch.load(path,map_location='cpu',weights_only=True)
                assert sha(path)==read(path.parent/'COMPLETED.json')['checkpoint_sha256']
                model=attention.build();model.load_state_dict(state['state_dict']);model.eval();self.att_members.append((model,state['scales']))
            self.att_load=elapsed(t)
    def union(self,t,qs):
        return query_table(np.asarray(t['coordinates']),np.asarray(t['labels']),np.array([q['coordinates'] for q in qs]),{k:v for k,v in public_input(t).items() if k!='coordinates'})
    def prepare(self,t,qs):
        g,o,v,ix=self.union(t,qs);tid=t['table_id'];members=[];start=stamp()
        for source,sc in self.p.learned.models['mlp']:
            model=copy.deepcopy(source);x=tensor(feature(g,sc));ys=np.asarray(sc['targets'][t['family']]);y=tensor(v/ys)
            opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=1e-4)
            for _ in range(self.p.learned.sel['mlp']['adapt_steps']):
                opt.zero_grad();loss=torch.nn.functional.huber_loss(model(x,o,y)[o],y);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
            model.eval();members.append((model,sc))
        self.cache[tid]=members
        self.prep.append(dict(task=self.kind,table_id=tid,method='mlp_adapt',stage='fit_once',support_count=len(o),query_labels_read=0,**elapsed(start)))
        if self.att:
            a=self.att
            for q in qs:a.GRIDS[(tid,tuple(q['coordinates']))]={'spec':q['spec']}
            start=stamp();am=[];x,pr=a.features(g)
            for source,sc in self.att_members:
                model=copy.deepcopy(source);ys=np.asarray(sc['targets'][t['family']]);unit=float(np.mean(ys));y=tensor(v/ys)
                opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=1e-4)
                for _ in range(self.att_steps):
                    opt.zero_grad();pred=a.forward(model,x[o],pr[o])*tensor(unit/ys);loss=torch.nn.functional.huber_loss(pred,y);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step()
                model.eval();am.append((model,sc))
            self.cache[tid+'attention']=am
            self.prep.append(dict(task=self.kind,table_id=tid,method='attentioncap_adapted',stage='fit_once',support_count=len(o),query_labels_read=0,**elapsed(start)))
    def predict(self,m,t,qs):
        start=stamp();st=dict(setup_s=0.,adapt_s=0.,encode_s=0.,numerical_s=0.,forward_s=0.,transfer_s=0.,postprocess_s=0.)
        z=time.perf_counter()
        if m in ['mlp_adapt','attentioncap_adapted']:
            # Fixed-S adaptation is already retained. A pointwise model needs
            # query geometry/context only; rebuilding an unused S+Q union would
            # artificially charge it for another estimator's input protocol.
            g=dict(public_input(t),coordinates=[q['coordinates'] for q in qs])
        else:g,o,v,ix=self.union(t,qs)
        st['encode_s']+=time.perf_counter()-z
        if m in ['full','binary','residual']:
            z=time.perf_counter();nt=[0.];original=episodes.support_state
            def timed(*args,**kwargs):
                t0=time.perf_counter();val=original(*args,**kwargs);nt[0]+=time.perf_counter()-t0;return val
            episodes.support_state=timed
            try:e=encode(g,o,v,self.p.scales,CLASSICAL if m=='full' else ('linear',))
            finally:episodes.support_state=original
            b=stack([e]);st['numerical_s']=nt[0];st['encode_s']+=time.perf_counter()-z-nt[0]
            members=self.p.members if m=='full' else self.p.control[m];outputs=[];ys=np.asarray(self.p.scales['targets'][t['family']]);z=time.perf_counter()
            with torch.inference_mode():
                for model in members:
                    out=model(b['features'],b['anchor'],b['gate'],b['delta'],b['valid'],padding=b['padding'],clamp_lower=b['lower'],clamp_upper=b['upper'],inside=b['inside'])
                    outputs.append(out[0,:e['n']].numpy()*ys)
            st['forward_s']=time.perf_counter()-z;z=time.perf_counter();pred=np.maximum(np.mean(outputs,axis=0),0);pred[o]=v;pred=pred[ix];st['postprocess_s']=time.perf_counter()-z
            st['geometry_tokens']=len(g['coordinates']);st['material_tokens']=len(g.get('materials') or [])
        elif m in ['mlp_adapt','attentioncap_adapted']:
            # These models predict structures independently; only Q is evaluated
            # after support-only fitting, with equivalence checked below.
            z=time.perf_counter();qg=dict(g,coordinates=[q['coordinates'] for q in qs]);out=[]
            members=self.cache[t['table_id']+('attention' if m.startswith('attention') else '')]
            if m=='mlp_adapt':x=tensor(feature(qg,members[0][1]))
            else:x,pr=self.att.features(qg)
            st['encode_s']+=time.perf_counter()-z;z=time.perf_counter()
            with torch.inference_mode():
                for model,sc in members:
                    ys=np.asarray(sc['targets'][t['family']])
                    out.append(np.maximum(model(x).numpy()*ys,0) if m=='mlp_adapt' else self.att.forward(model,x,pr).numpy()*float(np.mean(ys)))
            st['forward_s']=time.perf_counter()-z;z=time.perf_counter();pred=np.maximum(np.mean(out,axis=0),0);st['postprocess_s']=time.perf_counter()-z
        elif m=='cnp':
            # Keep all three original feature encodings and all S+Q predictions;
            # this only exposes the existing computation's timing boundaries.
            out=[]
            for model,sc in self.p.learned.models['cnp']:
                z=time.perf_counter();x=tensor(feature(g,sc));ys=np.asarray(sc['targets'][t['family']]);y=tensor(v/ys);st['encode_s']+=time.perf_counter()-z;z=time.perf_counter()
                with torch.inference_mode():p=model(x,o,y).numpy()*ys
                st['forward_s']+=time.perf_counter()-z;z=time.perf_counter();out.append(np.maximum(p,0));st['postprocess_s']+=time.perf_counter()-z
            z=time.perf_counter();pred=np.maximum(np.mean(out,axis=0),0);pred[o]=v;pred=pred[ix];st['postprocess_s']+=time.perf_counter()-z
        else:
            z=time.perf_counter();pred=self.p(m,g,o,v)[ix]
            st['numerical_s']=time.perf_counter()-z
        st.update(elapsed(start));st['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return pred,st

def main():
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['fem','native']);ap.add_argument('--pilot',action='store_true');a=ap.parse_args()
    environment();groups=workloads(a.kind);engine=Engine(a.kind);methods=METHODS+(['attentioncap_adapted'] if engine.att else [])
    start=stamp();equiv=[];old={(r['table_id'],r['query_id'],r['method']):r for r in map(json.loads,(OLD/f'predictions_{a.kind}.jsonl').read_text().splitlines())}
    for t,qs in groups:
        engine.prepare(t,qs)
        for m in methods:
            pp=[]
            for j in range(0,len(qs),32):
                batch=qs[j:j+32];pred,st=engine.predict(m,t,batch);pp.extend(pred)
            if m!='attentioncap_adapted':
                ref=np.array([old[t['table_id'],q['query_id'],m]['prediction'] for q in qs]);ys=np.array(engine.p.scales['targets'][t['family']]);err=float(np.max(abs(np.array(pp)-ref)/ys))
                passed=err<2e-6;equiv.append(dict(table_id=t['table_id'],method=m,max_source_scaled_error=err,passed=passed));assert passed,(t['table_id'],m,err)
        print('verified',a.kind,t['table_id'],flush=True)
    write(O/f'equivalence_{a.kind}.json',equiv);write(O/f'preparation_{a.kind}.json',dict(model_load=engine.load,attention_load=getattr(engine,'att_load',None),contexts=engine.prep))
    # Pilot uses the full canonical workload once; repetitions frozen afterwards.
    pilots=[]
    for m in methods:
        z=stamp()
        for t,qs in groups:
            for j in range(0,len(qs),32):engine.predict(m,t,qs[j:j+32])
        pilots.append(dict(method=m,**elapsed(z)))
    write(O/f'pilot_{a.kind}.json',dict(rows=pilots,blocks=20,warmups=3,inner_repetitions=1,reason='Each block covers the whole frozen population; individual calls use high-resolution clocks; C++ getter uses a separate long loop',batch_sizes=[32,1,8],seed=20261115))
    if a.pilot:return
    raw=[];predrows=[];rng=np.random.default_rng(20261115)
    for size in [32,1,8]:
        jobs=[(m,t,qs[j:j+size],j) for t,qs in groups for j in range(0,len(qs),size) for m in methods]
        for block in range(-3,20):
            for k in rng.permutation(len(jobs)):
                m,t,qs,j=jobs[k];pred,st=engine.predict(m,t,qs)
                if block>=0:raw.append(dict(task=a.kind,method=m,batch_limit=size,block=block,table_id=t['table_id'],batch_start=j,query_count=len(qs),support_count=len(t['coordinates']),cache_mode='weights resident; MLP/Attention support-fit retained; other numerical setup included; no answer cache',**st))
                if block==0:
                    for q,p in zip(qs,pred):predrows.append(dict(task=a.kind,method=m,batch_limit=size,table_id=t['table_id'],query_id=q['query_id'],geometry_hash=q['geometry_hash'],process=t['process_id'],family=t['family'],prediction=p.tolist(),reference=q['reference'],components=t['target_names'],unit=t['units'],occurrence_count=q['occurrence_count'],sampling_probability=q['sampling_probability']))
            if block in [-1,4,9,14,19]:print('timed',a.kind,size,block,elapsed(start),flush=True)
            assert elapsed(start)['cpu_s']<5*3600,'benchmark budget guard'
        csvwrite(O/f'timing_{a.kind}.csv',raw)
        (O/f'predictions_{a.kind}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in predrows))
    write(O/f'completed_{a.kind}.json',dict(**elapsed(start),timing_rows=len(raw),predictions=len(predrows),queries=sum(len(qs) for _,qs in groups),preparation=engine.prep,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
if __name__=='__main__':main()
