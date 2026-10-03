"""Run the released three-seed ensemble on one deterministic held-out episode."""
import argparse
import os
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from unified.score import load_members,predict_table
from pdkcap.common import read_tables
from pdkcap.sampling import mask
from pdkcap.train import unique_tables

def run(domain,root=None):
    root=Path(root or os.environ.get("RG_DATA_ROOT", ROOT))
    torch.set_num_threads(1)
    entry=json.loads((ROOT/'configs/paper_models.json').read_text())[domain]
    tables=unique_tables(read_tables(root/entry['cohort']))
    table=max(tables,key=lambda x:len(x['coordinates']))
    ckpts=[root/c['path'] for c in entry['checkpoints']]
    for p,c in zip(ckpts,entry['checkpoints']):
        if hashlib.sha256(p.read_bytes()).hexdigest()!=c['sha256']:raise ValueError(f'Checkpoint hash mismatch: {p}')
    members,scales=load_members(ckpts)
    observed,query=mask(table['coordinates'],'block',.5,11)
    truth=np.asarray(table['labels'],float)
    prediction,anchor,segment,target_scales=predict_table(members,scales,table,observed,truth[observed])
    assert np.array_equal(prediction[observed],truth[observed])
    assert np.isfinite(prediction).all()
    return dict(domain=domain,table_id=table['table_id'],points=len(truth),observed=observed.tolist(),query=query.tolist(),
                target_names=table['target_names'],units=table['units'],prediction=prediction.tolist(),
                query_mae=float(abs(prediction[query]-truth[query]).mean()),observed_values_preserved=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--domain',choices=['public','reference','to_asap7'],default='reference');p.add_argument('--output',type=Path)
    a=p.parse_args();r=run(a.domain)
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ['observed','query','prediction']},indent=2))
    print('This is a smoke example, not an aggregate paper score.')

if __name__=='__main__':main()
