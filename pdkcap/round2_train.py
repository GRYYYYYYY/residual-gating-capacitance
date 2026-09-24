"""Round-two equal-protocol validation and matched width-aware training."""
import argparse
import collections
import json
import time
from pathlib import Path
import numpy as np
import torch
from .budget import allocation
from .common import ROOT,FAMILIES,read_tables,write_json,file_hash
from .metrics import record,summarize
from .model import ConditionalModel,GroupDRO,fit_scales,encode
from .round2_model import GatedModel,inputs,predict_round2,correct,support_geometry
from .sampling import mask
from .train import unique_tables

RATIOS=(.1,.3,.5,.7)
MASK_SEEDS=(11,29,47,71,101)


def episodes(tables):
    for protocol in ('mcar','block','extrapolation','width'):
        eligible=[t for t in tables if len(t['coordinates'])>=2 and (protocol!='width' or t['width_count']>1)]
        if not eligible:continue
        for ratio in ((None,) if protocol=='width' else RATIOS):
            seeds=range(max(t['width_count'] for t in eligible)) if protocol=='width' else MASK_SEEDS
            for seed in seeds:
                for t in eligible:
                    if protocol=='width' and seed>=t['width_count']:continue
                    observed,hidden=mask(t['coordinates'],protocol,ratio,seed)
                    yield t,protocol,ratio,seed,observed,hidden


def scores(records):
    groups=collections.defaultdict(list)
    for r in records:groups[(r['method'],r['protocol'],r['ratio'],r['mask_seed'])].append(r)
    cells=[dict(method=m,protocol=p,ratio=r,mask_seed=s,**summarize(rs)) for (m,p,r,s),rs in groups.items()]
    protocols=collections.defaultdict(list)
    for c in cells:
        if c['nrmse'] is not None:protocols[(c['method'],c['protocol'])].append(c['nrmse'])
    pm={}
    for (m,p),v in protocols.items():pm.setdefault(m,{})[p]=float(np.mean(v))
    return dict(objectives={m:float(np.mean(list(v.values()))) for m,v in pm.items()},protocol_means=pm,cells=cells)


def validate(model,tables,scales):
    rows=[]
    for t,protocol,ratio,seed,o,q in episodes(tables):
        y=np.asarray(t['labels']);x=np.asarray(t['coordinates'])
        base=predict_round2(model,t,o,y[o],scales)
        geometry=support_geometry(x[o],y[o],x,scales['targets'][t['family']],len(x))
        for correction in ('none','local','boundary','both'):
            p,_=correct(base,geometry,correction)
            rows.append(record(t,y[q],p[q],method=correction,protocol=protocol,ratio=ratio,mask_seed=seed))
    return scores(rows)


def execute(a):
    a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(a.seed)
    rng=np.random.default_rng(a.seed);tables=read_tables(a.data)
    if any(t['partition'] not in ('train','val') for t in tables):
        raise PermissionError('training runner accepts train/validation-only files, never test or confirmation')
    training=unique_tables([t for t in tables if t['partition']=='train' and len(t['coordinates'])>=2])
    validation=unique_tables([t for t in tables if t['partition']=='val' and len(t['coordinates'])>=2])
    scales=fit_scales(training);targets=len(training[0]['labels'][0])
    model=GatedModel(targets) if a.variant=='gated' else ConditionalModel('residual',targets=targets)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=1e-4);dro=GroupDRO(a.eta)
    groups={g:[t for t in training if t['family']==f] for g,f in enumerate(FAMILIES)}
    source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sorted((ROOT/'pdkcap').glob('*.py'))}
    write_json(a.output/'config.json',dict(arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
        data_sha256=file_hash(a.data),protocol_sha256=file_hash(ROOT/'configs/round2_protocol.json'),source_hashes=source_hashes,
        scales=scales,training_tables=len(training),validation_tables=len(validation),endpoint='last step',
        gate_initialization='zero final layer gives g=0.5; hidden layer default initialization',
        label_access='train and validation only',width_episodes=True))
    start=time.perf_counter();history=[]
    for step in range(a.steps):
        model.train();optimizer.zero_grad();losses={}
        for g,ts in groups.items():
            processes=sorted({t['process_id'] for t in ts});process=processes[int(rng.integers(len(processes)))]
            pool=[t for t in ts if t['process_id']==process];t=pool[int(rng.integers(len(pool)))]
            protocols=['mcar','block','extrapolation']+(['width'] if t['width_count']>1 else [])
            protocol=protocols[int(rng.integers(len(protocols)))];ratio=RATIOS[int(rng.integers(4))]
            o,q=mask(t['coordinates'],protocol,ratio,int(rng.integers(2**31)));y=np.asarray(t['labels'])
            if isinstance(model,GatedModel):
                f,b,s,geometry,_=inputs(t,o,y[o],scales)
                predicted=model(f[None],b[None],geometry=geometry[None])[0,q]
            else:
                f,b,s=encode(t,o,y[o],scales);predicted=model(f[None],b[None])[0,q]
            target=torch.tensor(y[q]/s,dtype=torch.float32)
            losses[g]=torch.nn.functional.huber_loss(predicted,target,delta=1.)
        loss=dro.loss(losses);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
        if step%100==0 or step==a.steps-1:
            history.append(dict(step=step+1,loss=float(loss.detach()),weights=dro.weights.tolist()))
            print(json.dumps(dict(step=step+1,steps=a.steps,seconds=time.perf_counter()-start)),flush=True)
    training_seconds=time.perf_counter()-start
    torch.save(dict(state_dict=model.state_dict(),variant='residual',model_version=GatedModel.version if isinstance(model,GatedModel) else 'residual-width-v1',
                    targets=targets,scales=scales,training_protocol='round2',width_episodes=True),a.output/'checkpoint.pt')
    validation_result=validate(model,validation,scales) if a.purpose=='formal' else None
    write_json(a.output/'result.json',dict(status='completed',purpose=a.purpose,training_wall_seconds=training_seconds,
        total_wall_seconds=time.perf_counter()-start,steps=a.steps,history=history,validation=validation_result,
        checkpoint_sha256=file_hash(a.output/'checkpoint.pt')))


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--variant',choices=['residual','gated'],default='gated');p.add_argument('--steps',type=int,default=2000)
    p.add_argument('--seed',type=int,default=0);p.add_argument('--eta',type=float,default=0.)
    p.add_argument('--purpose',choices=['profile','formal'],default='profile');p.add_argument('--slot-seconds',type=int,default=3600)
    a=p.parse_args()
    if a.purpose=='profile' and a.steps>100:raise ValueError('profile at most 100 steps')
    if a.purpose=='formal' and a.steps!=2000:raise ValueError('formal frozen endpoint is 2000 steps')
    with allocation('training','round2 '+str(a.output),a.slot_seconds):execute(a)

if __name__=='__main__':main()
