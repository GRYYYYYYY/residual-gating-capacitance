"""Matched-budget controls, without changing any archived training code/run.
Run from any directory. All fits reuse each headline member's train pool,
initial residual checkpoint, random seed, episode sampler, objective and budget.
"""
import os, sys, json, argparse, copy
from pathlib import Path
sys.dont_write_bytecode = True
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
CODE=Path(__file__).resolve().parent
ROOT=CODE.parents[1]
HERE=Path(os.environ.get('RG_CONTROL_ROOT', CODE)).resolve()
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from torch import nn
from unified import train as original
from unified.episodes import encode as original_encode
from unified.workspace import file_hash, ARCHIVE

class SimpleControl(nn.Module):
    def __init__(self, base, variant):
        super().__init__()
        self.input=base.input; self.encoder=base.encoder; self.residual=base.residual
        self.variant=variant; self.targets=base.targets
        if variant=='binary':
            # Anchor/raw-neural only: no clipped reading, analytic proposals,
            # agreement descriptors or unused output slots.
            first=base.gate[0]
            self.gate=nn.Sequential(nn.Linear(first.in_features-3*base.targets,first.out_features),nn.ReLU(),nn.Linear(first.out_features,2*base.targets))
            with torch.no_grad():
                self.gate[0].weight.copy_(first.weight[:,:self.gate[0].in_features]);self.gate[0].bias.copy_(first.bias)
                self.gate[-1].weight.zero_();self.gate[-1].bias.zero_()
            self.gate_bias=nn.Parameter(torch.zeros(2))
            self.log_temperature=nn.Parameter(base.log_temperature.detach().clone())
    def forward(self, features, baseline, gate_features, delta, valid, padding=None, **kwargs):
        hidden=self.encoder(self.input(features),src_key_padding_mask=padding)
        residual=self.residual(hidden)
        if self.variant=='binary':
            logits=self.gate(torch.cat([hidden,gate_features],dim=-1)).reshape(*hidden.shape[:2],2,self.targets)
            logits=logits+self.gate_bias.view(1,1,2,1)
            temperature=torch.nn.functional.softplus(self.log_temperature)+1e-3
            residual=residual*torch.softmax(logits/temperature,dim=2)[:,:,1]
        return torch.clamp(baseline+residual,min=0.)

def config_for(domain,seed):
    pattern={'public':'holdout_g_s{}','reference':'v10_reference_all_s{}','to_asap7':'v10_to_asap7_all_s{}'}[domain]
    path=ARCHIVE/'runs'/pattern.format(seed)/'FROZEN.json'
    cfg=copy.deepcopy(json.loads(path.read_text())['config'])
    for key in ['data','scales_from','init_from']:
        p=Path(cfg[key]);cfg[key]=str(p if p.is_absolute() else ARCHIVE/p)
    return cfg,path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--domain',required=True);ap.add_argument('--variant',choices=['residual','binary'],required=True);ap.add_argument('--seed',type=int,required=True);ap.add_argument('--smoke',action='store_true');a=ap.parse_args()
    cfg,source=config_for(a.domain,a.seed)
    out=HERE/('smoke' if a.smoke else 'runs')/f'{a.domain}_{a.variant}_s{a.seed}';out.mkdir(parents=True,exist_ok=False)
    if a.smoke:cfg['steps']=2
    factory=original.build_model
    def build(*args):return SimpleControl(factory(*args),a.variant)
    original.build_model=build
    # Skips unused analytic computations; token/support inputs stay identical.
    original.encode=lambda t,o,y,s:original_encode(t,o,y,s,names=('linear',))
    (out/'FROZEN.json').write_text(json.dumps(dict(config=cfg,variant=a.variant,source=str(source),source_sha256=file_hash(source),runner_sha256=file_hash(__file__),selection='last step; no new validation-based tuning',control='same train pool, warm start, seed, sampler, optimizer, objective, updates and ensemble size'),indent=2))
    original.train(cfg,out)
    print('CONTROL_COMPLETE',str(out),flush=True)
if __name__=='__main__':main()
