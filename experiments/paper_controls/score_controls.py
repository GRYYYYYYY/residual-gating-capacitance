"""Evaluate new controls on the original 30% / five-mask-seed episodes.
Local affine extrapolation is selected on validation BEFORE confirmation.
Records retain the published aggregation schema and support-region assignment.
"""
import os,sys,json,gzip,argparse,functools
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
sys.dont_write_bytecode=True
from run_controls import HERE,ROOT,SimpleControl,config_for
import numpy as np
import torch
from unified import train as original
from unified.episodes import encode,stack
from unified.aggregate import add_records,mask_macro_nrmse
from unified.regime import regroup
from unified.score import dependency_group, load_members
from unified.workspace import ARCHIVE,file_hash
from pdkcap.common import read_tables
from pdkcap.train import unique_tables
from pdkcap.sampling import mask
from pdkcap.metrics import record
from pdkcap.round3_support import SEGMENTS

PROTOCOLS=('mcar','block','extrapolation')
SEEDS=(11,29,47,71,101)
NEIGHBORS=(2,4,8,16)
CONF={'public':'public_retrospective_original','reference':'reference_confirmation_round3_main','to_asap7':'to_asap7_confirmation_round3_main'}
FULL={'public':('conf_public_holdout','sace_r_holdout'),'reference':('conf_v10_reference','v10_all'),'to_asap7':('conf_v10_to_asap7','v10_all')}
MEMBERS={}
def load(domain):
    torch.set_num_threads(1)
    scales=original.load_scales(config_for(domain,0)[0]['scales_from'])
    models={}
    for variant in ['residual','binary']:
        models[variant]=[]
        for seed in range(3):
            state=torch.load(HERE/'runs'/f'{domain}_{variant}_s{seed}'/'checkpoint.pt',map_location='cpu',weights_only=True)
            cfg,_=config_for(domain,seed)
            base=original.build_model(cfg,state['features_in'],state['gate_in'],state['experts'],state['targets'])
            model=SimpleControl(base,variant);model.load_state_dict(state['state_dict']);model.eval()
            assert state['scales']==scales
            models[variant].append(model)
    fullpaths=[config_for(domain,s)[1].parent/'checkpoint.pt' for s in range(3)]
    models['full_replayed'],fullscales=load_members(fullpaths)
    assert fullscales==scales
    return models,scales

def affine_predict(xo,yo,x,k):
    """Local affine fit in observed-range-normalized independent coordinates.
    Each query uses k nearest supports (at least rank+1), equal weights,
    an unpenalized intercept and 1e-8 ridge on slopes; no hull clamping.
    """
    span=np.ptp(xo,axis=0);span=np.where(span>1e-12,span,1.)
    origin=xo.mean(0);z=(xo-origin)/span;q=(x-origin)/span
    _,s,v=np.linalg.svd(z,full_matrices=False)
    rank=int((s>max(s[0] if len(s) else 0,1.)*1e-10).sum())
    if not rank:return np.broadcast_to(yo.mean(0),(len(x),yo.shape[1])).copy()
    z=z@v[:rank].T;q=q@v[:rank].T
    count=min(len(xo),max(k,rank+1))
    ids=np.argsort(((q[:,None,:]-z[None,:,:])**2).sum(-1),axis=1,kind='stable')[:,:count]
    design=np.concatenate([np.ones((len(x),count,1)),z[ids]-q[:,None,:]],axis=-1)
    gram=np.einsum('nki,nkj->nij',design,design)
    gram+=np.diag([0.]+[1e-8]*rank)[None]
    rhs=np.einsum('nki,nkt->nit',design,yo[ids])
    coefs=np.linalg.solve(gram,rhs)
    return np.maximum(coefs[:,0],0.)

def worker(task):
    domain,table,kind,chosen=task
    if domain not in MEMBERS:
        if kind=='learned':MEMBERS[domain]=load(domain)
        else:MEMBERS[domain]=(None,original.load_scales(config_for(domain,0)[0]['scales_from']))
    models,scales=MEMBERS[domain]
    y=np.asarray(table['labels'],float);x=np.asarray(table['coordinates'],float)
    out=[]
    for protocol in PROTOCOLS:
        for seed in SEEDS:
            o,q=mask(x,protocol,.3,seed)
            enc=encode(table,o,y[o],scales,names=('linear',));ys=np.asarray(enc['scales'])
            predictions={}
            if kind=='learned':
                b=stack([enc])
                with torch.inference_mode():
                    for variant,ms in models.items():
                        batch=stack([encode(table,o,y[o],scales)]) if variant=='full_replayed' else b
                        values=[m(batch['features'],batch['anchor'],batch['gate'],batch['delta'],batch['valid'],padding=batch['padding'],clamp_lower=batch['lower'],clamp_upper=batch['upper'],inside=batch['inside'])[0,:len(x)].numpy()*ys for m in ms]
                        predictions[variant]=np.mean(values,axis=0)
                        for j,val in enumerate(values):predictions[f'{variant}_seed{j}']=val
            else:
                for k in (NEIGHBORS if chosen is None else [chosen]):predictions[f'local_affine_k{k}']=affine_predict(x[o],y[o],x,k)
            regions=[('all',q)]+[(name,q[enc['segment'][q]==j]) for j,name in enumerate(SEGMENTS)]
            for name,pred in predictions.items():
                pred[o]=y[o]
                assert np.isfinite(pred).all()
                for region,idx in regions:
                    if not len(idx):continue
                    out.append(record(table,y[idx],pred[idx],method=name,training_seed='ensemble',protocol=protocol,ratio=.3,mask_seed=seed,segment=region,requested_n=len(idx),coverage=1.,scored_indices=idx.tolist(),training_scale=ys.tolist(),dependency_group=dependency_group(table)))
    return out

def evaluate(domain,kind,cohort,output,chosen=None,workers=2):
    ts=unique_tables(read_tables(cohort))
    with gzip.open(output,'xt') as f:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for rows in pool.map(worker,[(domain,t,kind,chosen) for t in ts]):
                for r in rows:f.write(json.dumps(r,allow_nan=False)+'\n')
    return len(ts)

def scores(path,methods):
    acc={};add_records(acc,path);groups=regroup(acc)
    return {m:{f'{regime}/{p}':mask_macro_nrmse(g,m,p,.3,training_seed='ensemble') for regime,g in groups.items() for p in PROTOCOLS} for m in methods}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--domain',required=True);ap.add_argument('--kind',choices=['learned','affine'],required=True);ap.add_argument('--workers',type=int,default=2);a=ap.parse_args()
    dest=HERE/'scores'/a.domain;dest.mkdir(parents=True,exist_ok=True)
    conf=ARCHIVE/'runs/round3_evaluation_inputs_v1'/f'{CONF[a.domain]}.jsonl'
    if a.kind=='affine':
        val=ARCHIVE/'runs/round3_validation_inputs_v1'/f'{a.domain}_val.jsonl'
        if a.domain=='public':
            # Same downstream exclusion as the retrained headline public model.
            ts=[t for t in read_tables(config_for(a.domain,0)[0]['data']) if t['partition']=='val']
            val=dest/'public_holdout_val.jsonl';val.write_text(''.join(json.dumps(t)+'\n' for t in ts))
        if a.domain=='to_asap7':assert {t['process_id'] for t in read_tables(val)}=={'freepdk15'}
        vf=dest/'affine_validation.jsonl.gz';evaluate(a.domain,'affine',val,vf,workers=a.workers)
        vs=scores(vf,[f'local_affine_k{k}' for k in NEIGHBORS])
        objective={m:float(np.mean([v for v in ss.values() if v is not None])) for m,ss in vs.items()}
        best=min(objective,key=objective.get);k=int(best.rsplit('k',1)[1])
        receipt=dict(validation=str(val),validation_sha256=file_hash(val),candidates=vs,objective=objective,selected=best,criterion='equal mean over defined inside/outside x random/block/extrapolation cells at 30%; five fixed mask seeds',confirmation_read_for_selection=False)
        (dest/'affine_selection.json').write_text(json.dumps(receipt,indent=2))
        output=dest/'affine_confirmation.jsonl.gz';evaluate(a.domain,'affine',conf,output,k,a.workers)
        result=scores(output,[best])
    else:
        output=dest/'learned_confirmation.jsonl.gz';evaluate(a.domain,'learned',conf,output,workers=a.workers)
        result=scores(output,['residual','binary','full_replayed']+[f'{v}_seed{s}' for v in ['residual','binary','full_replayed'] for s in range(3)])
    (dest/f'{a.kind}_summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
if __name__=='__main__':main()
