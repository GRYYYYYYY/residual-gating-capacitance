import sys,json,hashlib,gzip,os
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'experiments/paper_controls'))
from experiments.dac_characterization_20261114.common import tables,source_config,public_input,PATHS,MODELS,sha
from unified.train import build_model,episode_loss
from unified.episodes import encode,stack,RATIOS
from unified.basis import CLASSICAL
from unified.score import predict_table,dependency_group,load_members
from unified.workspace import FAMILIES
from pdkcap.sampling import mask,geometry_order
from run_controls import SimpleControl
from paths import OUT,CODE,DOC,OLD,ATTEMPT,SETTINGS,atomic_json
from gates import freeze_gate,worker_gate,endpoint_gate
from checks import assert_same_encoded
torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False)
def source(a,s):
 return ROOT/MODELS['reference']['checkpoints'][s]['path'] if a=='Full' else Path(PATHS['control_root'])/'runs'/f'reference_binary_s{s}'/'checkpoint.pt'
def load(a,s,path=None):
 p=path or source(a,s);state=torch.load(p,map_location='cpu',weights_only=True)
 cfg=dict(source_config('reference',s));cfg['init_from']=None
 model=build_model(cfg,state['features_in'],state['gate_in'],state['experts'],state['targets'])
 if a=='binary':model=SimpleControl(model,'binary')
 model.load_state_dict(state['state_dict'],strict=True);model.eval()
 return model,state,cfg
def names(a):return CLASSICAL if a=='Full' else ('linear',)
def episodes():
 with gzip.open(OUT/'EPISODE_PLAN.json.gz','rt') as f:return json.load(f)
def check_frozen():return freeze_gate()
def table_hash(t):return hashlib.sha256(json.dumps(t,sort_keys=True).encode()).hexdigest()
def verified_tables(split):
 ts=tables('reference',split);manifest=json.loads((OUT/'DATA_MANIFEST.json').read_text());expected={r['table_id']:r['content_sha256'] for r in manifest if r['split']==split}
 assert {t['table_id']:table_hash(t) for t in ts}==expected,'actual table content changed'
 return ts
