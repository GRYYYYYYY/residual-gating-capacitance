"""Frozen-endpoint training with process/duplicate-aware balanced episodes."""
import argparse
import json
import time
import numpy as np
import torch
from .common import FAMILIES,read_tables,write_json,file_hash
from .sampling import mask
from .model import ConditionalModel,GroupDRO,encode,fit_scales,predict_model
from .metrics import record,summarize
from pathlib import Path
from .budget import allocation


def unique_tables(tables):
    seen=set(); result=[]
    for t in tables:
        # Exact duplicates do not buy additional training/evaluation weight.
        key=tuple(t['curve_hashes']) if 'curve_hashes' in t else t['table_id']
        if key not in seen: seen.add(key); result.append(t)
    return result


def validate(model,tables,scales):
    output={}
    for protocol in ('mcar','block','extrapolation'):
        seed_scores=[]
        for seed in (11,29,47,71,101):
            rows=[]
            for t in tables:
                if len(t['coordinates'])<2: continue
                o,q=mask(t['coordinates'],protocol,.3,seed)
                y=np.asarray(t['labels']); pred=predict_model(model,t,o,y[o],scales)
                rows.append(record(t,y[q],pred[q]))
            if rows: seed_scores.append(summarize(rows)['nrmse'])
        if seed_scores: output[protocol]=float(np.mean(seed_scores))
    return output


def main():
    p=argparse.ArgumentParser(); p.add_argument('--data',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); p.add_argument('--steps',type=int,default=2000)
    p.add_argument('--seed',type=int,default=0); p.add_argument('--variant',choices=['direct','residual'],default='residual')
    p.add_argument('--eta',type=float,default=0.); p.add_argument('--device',default='cpu')
    p.add_argument('--purpose',choices=['profile','formal'],default='profile'); a=p.parse_args()
    if a.purpose=='formal':
        if a.device!='cpu':raise PermissionError('current authorization is CPU-only')
        with allocation('training',str(a.output),600):
            execute(a)
    else:
        if a.steps>100:raise ValueError('engineering profiles are limited to 100 steps')
        execute(a)


def execute(a):
    a.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1); torch.manual_seed(a.seed); rng=np.random.default_rng(a.seed)
    tables=read_tables(a.data)
    training=unique_tables([t for t in tables if t['partition']=='train' and len(t['coordinates'])>=2])
    validation=unique_tables([t for t in tables if t['partition']=='val' and len(t['coordinates'])>=2])
    scales=fit_scales(training)
    targets=len(training[0]['target_names'])
    model=ConditionalModel(a.variant,targets=targets).to(a.device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-3,weight_decay=1e-4)
    dro=GroupDRO(a.eta)
    groups={g:[t for t in training if t['family']==family] for g,family in enumerate(FAMILIES)}
    write_json(a.output/'config.json',dict(arguments={k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()},
        data_sha256=file_hash(a.data),scales=scales,training_tables=len(training),validation_tables=len(validation),
        label_access='training + validation only; no test evaluation',endpoint='last step',
        source_hashes={p.name:file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))}))
    started=time.perf_counter(); cpu_started=time.process_time(); history=[]
    for step in range(a.steps):
        model.train(); optimizer.zero_grad(); losses={}
        for g,ts in groups.items():
            processes=sorted({t['process_id'] for t in ts}); process=processes[int(rng.integers(len(processes)))]
            pool=[t for t in ts if t['process_id']==process]; t=pool[int(rng.integers(len(pool)))]
            protocol=('mcar','block','extrapolation')[int(rng.integers(3))]
            ratio=(.1,.3,.5,.7)[int(rng.integers(4))]
            o,q=mask(t['coordinates'],protocol,ratio,int(rng.integers(2**31)))
            y=np.asarray(t['labels']); f,b,s=encode(t,o,y[o],scales)
            pred=model(f[None].to(a.device),b[None].to(a.device))[0,q]
            target=torch.tensor(y[q]/s,dtype=torch.float32,device=a.device)
            losses[g]=torch.nn.functional.huber_loss(pred,target,delta=1.)
        loss=dro.loss(losses); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
        optimizer.step()
        if step%20==0 or step==a.steps-1:
            history.append(dict(step=step+1,loss=float(loss.detach()),group_weights=dro.weights.tolist()))
    elapsed=time.perf_counter()-started; cpu=time.process_time()-cpu_started
    # Profiles are engineering throughput checks, NOT method evidence or selection runs.
    validation_result=validate(model,validation,scales) if a.purpose=='formal' else None
    torch.save(dict(state_dict=model.state_dict(),variant=a.variant,targets=targets,scales=scales),a.output/'checkpoint.pt')
    write_json(a.output/'result.json',dict(status='completed',purpose=a.purpose,steps=a.steps,
        wall_seconds=elapsed,cpu_seconds=cpu,steps_per_second=a.steps/elapsed,
        validation_nrmse=validation_result,history=history,checkpoint_sha256=file_hash(a.output/'checkpoint.pt')))
    print(json.dumps(dict(output=str(a.output),seconds=elapsed,validation=validation_result)))

if __name__=='__main__':main()
