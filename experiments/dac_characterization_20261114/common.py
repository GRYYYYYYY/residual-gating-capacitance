"""Frozen artifact paths and label-free predictor inputs."""
import json, hashlib, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
PATHS=json.loads((HERE/'paths.json').read_text())
MODELS=json.loads((ROOT/'configs/paper_models.json').read_text())
from pdkcap.common import read_tables
from pdkcap.train import unique_tables
from unified.score import load_members

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def write(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False)
def public_input(t):
    keys=('table_id','domain','process_id','family','coordinates','units','target_names','metal','context_below','context_above','material_features','materials','width_count','split_group')
    return {k:t[k] for k in keys if k in t}
def source_config(setting,seed=0):
    p=ROOT/MODELS[setting]['checkpoints'][seed]['path']
    return json.loads((p.parent/'FROZEN.json').read_text())['config']
def tables(setting,split):
    cfg=source_config(setting)
    if split=='train':
        ts=[t for t in read_tables(ROOT/cfg['data']) if t['partition']=='train']
        # Transfer's data file is already source-only; assert below.
    elif split=='val':
        if setting=='public':ts=[t for t in read_tables(ROOT/cfg['data']) if t['partition']=='val']
        else:ts=read_tables(ROOT/f'runs/round3_validation_inputs_v1/{setting}_val.jsonl')
    else:ts=read_tables(ROOT/MODELS[setting]['cohort'])
    if setting=='to_asap7' and split in ('train','val'):assert {t['process_id'] for t in ts}=={'freepdk15'}
    return unique_tables(ts)
def full(setting):
    ps=[ROOT/c['path'] for c in MODELS[setting]['checkpoints']]
    for p,c in zip(ps,MODELS[setting]['checkpoints']):assert sha(p)==c['sha256']
    return load_members(ps)
def controls(setting,scales):
    import torch
    sys.path.insert(0,str(ROOT/'experiments/paper_controls'))
    from run_controls import SimpleControl
    from unified.train import build_model
    out={}
    for variant in ('residual','binary'):
        out[variant]=[]
        for seed in range(3):
            d=Path(PATHS['control_root'])/'runs'/f'{setting}_{variant}_s{seed}'
            receipt=json.loads((d/'COMPLETED.json').read_text());frozen=json.loads((d/'FROZEN.json').read_text())
            assert receipt['steps']==source_config(setting,seed)['steps']
            assert receipt['checkpoint_sha256']==sha(d/'checkpoint.pt')
            assert frozen['variant']==variant
            state=torch.load(d/'checkpoint.pt',map_location='cpu',weights_only=True)
            assert state['scales']==scales
            model=SimpleControl(build_model(source_config(setting,seed),state['features_in'],state['gate_in'],state['experts'],state['targets']),variant)
            model.load_state_dict(state['state_dict']);model.eval();out[variant].append(model)
    return out
