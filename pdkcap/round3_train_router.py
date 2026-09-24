"""Balanced OOF risk regression with a classical-regret penalty; no validation labels."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from torch.nn import functional as F
from .common import ROOT, file_hash, write_json
from .budget import allocation
from .round3_router import RiskRouter


def load_training(folder):
    receipt=json.loads((folder/'COMPLETED.json').read_text())
    features=[];risk=[];valid=[];weight=[];strata=[]
    for shard in receipt['shards']:
        if file_hash(shard['path'])!=shard['sha256'] or file_hash(shard['metadata'])!=shard['metadata_sha256']:
            raise ValueError('OOF shard drift')
        meta=json.loads(Path(shard['metadata']).read_text())
        with np.load(shard['path'],allow_pickle=False) as data:
            features.append(data['features']);risk.append(data['risk']);valid.append(data['valid']);weight.append(data['weight'])
            strata.extend([(meta['process'],meta['family'],int(s)) for s in data['segment']])
    x=np.concatenate(features);y=np.concatenate(risk);v=np.concatenate(valid);w=np.concatenate(weight)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (y<0).any():raise ValueError('invalid training arrays')
    if not v.any(axis=1).all():raise ValueError('no valid experts')
    index={s:i for i,s in enumerate(sorted(set(strata)))};groups=np.array([index[s] for s in strata])
    totals=np.bincount(groups,weights=w);w=w/totals[groups];w=w/w.sum()
    mean=np.sum(x*w[:,None],axis=0);variance=np.sum((x-mean)**2*w[:,None],axis=0)
    scale=np.sqrt(variance);scale[scale<1e-8]=1.
    return (x-mean)/scale,np.log(np.maximum(y,1e-12)),v,w,mean,scale,receipt['expert_names']


def objective(predicted,truth,valid,classical,penalty,temperature=.5):
    active=valid[:,:,None].expand_as(truth)
    regression=F.huber_loss(predicted[active],truth[active],delta=1.)
    masked=predicted.masked_fill(~active,float('inf'))
    probabilities=torch.softmax(-masked/temperature,dim=1)
    realized=(probabilities*truth).sum(dim=1)
    classical_valid=active & classical[None,:,None]
    if not classical_valid.any(dim=1).all():raise ValueError('no applicable classical comparator')
    best=truth.masked_fill(~classical_valid,float('inf')).min(dim=1).values
    regret=torch.relu(realized-best).mean()
    return regression+penalty*regret,regression,regret


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--penalty',type=float,required=True);a=p.parse_args()
    config=json.loads((ROOT/'configs/round3_router_training.json').read_text())
    if a.seed not in config['training_seeds'] or a.penalty not in config['regret_penalties']:raise ValueError('configuration outside frozen candidate set')
    a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1);torch.manual_seed(a.seed)
    with allocation('training','round3 risk router '+str(a.output),3600):
        x,y,v,w,mean,scale,names=load_training(a.data)
        model=RiskRouter(x.shape[1],len(names),y.shape[2])
        optimizer=torch.optim.AdamW(model.parameters(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
        xt=torch.tensor(x,dtype=torch.float32);yt=torch.tensor(y,dtype=torch.float32);vt=torch.tensor(v)
        classical=torch.tensor([n in ('linear','pchip','width_linear') or n.startswith('gp_') for n in names])
        write_json(a.output/'FROZEN.json',dict(data_receipt_sha256=file_hash(a.data/'COMPLETED.json'),
            training_config_sha256=file_hash(ROOT/'configs/round3_router_training.json'),seed=a.seed,penalty=a.penalty,
            rows=len(x),mean=mean.tolist(),scale=scale.tolist(),expert_names=names,
            source_hashes={str(p):file_hash(p) for p in [Path(__file__).resolve(),ROOT/'pdkcap/round3_router.py']},
            label_access='OOF original training records only; no validation/test/confirmation'))
        rng=np.random.default_rng(a.seed);history=[];started=time.perf_counter()
        for step in range(config['steps']):
            ids=rng.choice(len(x),size=config['batch_size'],replace=True,p=w)
            optimizer.zero_grad();output=model(xt[ids])
            loss,regression,regret=objective(output,yt[ids],vt[ids],classical,a.penalty,config['softmin_temperature'])
            if not torch.isfinite(loss):raise ValueError('nonfinite training loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),config['gradient_clip']);optimizer.step()
            if step%100==0 or step==config['steps']-1:
                row=dict(step=step+1,loss=float(loss.detach()),regression=float(regression.detach()),regret=float(regret.detach()))
                history.append(row);print(json.dumps(row),flush=True)
        torch.save(dict(state_dict=model.state_dict(),features=x.shape[1],experts=len(names),targets=y.shape[2],
            mean=mean.tolist(),scale=scale.tolist(),expert_names=names,version='round3-risk-router-v1',seed=a.seed,penalty=a.penalty),a.output/'checkpoint.pt')
        write_json(a.output/'COMPLETED.json',dict(steps=config['steps'],wall_seconds=time.perf_counter()-started,history=history,
            checkpoint_sha256=file_hash(a.output/'checkpoint.pt'),status='trained fixed endpoint; validation selection pending'))


if __name__=='__main__':main()
