"""Bounded C1/C3 training; original budgets, samplers and final-step selection."""
import os,sys,json,argparse,subprocess,concurrent.futures,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R));sys.path.insert(0,str(R/'experiments/paper_controls'))
O=R/'results/dac_main13_integrated_revision/main13_20261117/controls'
import torch
from torch import nn
from unified import train as original
from run_controls import config_for
class NumericalGate(nn.Module):
 def __init__(self,base):
  super().__init__();self.targets=base.targets;self.experts=base.experts-2
  width=base.gate[0].in_features-base.input.out_features
  self.gate=nn.Sequential(nn.Linear(width,base.gate[0].out_features),nn.ReLU(),nn.Linear(base.gate[0].out_features,self.experts*self.targets))
  nn.init.zeros_(self.gate[-1].weight);nn.init.zeros_(self.gate[-1].bias)
  self.gate_bias=nn.Parameter(base.gate_bias[:-2].detach().clone());self.log_temperature=nn.Parameter(base.log_temperature.detach().clone())
 def forward(self,features,baseline,gate_features,delta,valid,padding=None,return_gate=False,**kw):
  c=torch.nan_to_num(delta);w=valid.unsqueeze(-1).to(c.dtype);n=w.sum(2).clamp(min=1)
  mean=(c*w).sum(2)/n;sd=(((c-mean.unsqueeze(2))*w).square().sum(2)/n+1e-12).sqrt()
  span=torch.where(w>0,c,-1e30).amax(2)-torch.where(w>0,c,1e30).amin(2)
  x=torch.cat([gate_features,*[torch.sign(a)*torch.log1p(abs(a)) for a in [mean,sd,span]]],-1)
  logits=self.gate(x).reshape(*baseline.shape[:2],self.experts,self.targets)+self.gate_bias.view(1,1,-1,1)
  weights=torch.softmax(logits.masked_fill(~valid.unsqueeze(-1),-1e9)/(torch.nn.functional.softplus(self.log_temperature)+1e-3),2)
  p=(baseline+(weights*c).sum(2)).clamp(min=0)
  return (p,dict(weights=weights,valid=valid)) if return_gate else p
def train(domain,variant,seed):
 cfg,source=config_for(domain,seed);out=O/f'{domain}_{variant}_s{seed}';out.mkdir(parents=True,exist_ok=False)
 # config_for binds all source paths to the existing archive.
 if variant=='no_agreement':cfg['agreement']=False
 factory=original.build_model
 if variant=='numerical_gate':original.build_model=lambda *a:NumericalGate(factory(*a))
 frozen=dict(config=cfg,variant=variant,source=str(source),selection='final step, no configuration grid; original source selection frozen',training_labels='source fitting only',source_sha256=original.file_hash(source),runner_sha256=original.file_hash(__file__))
 (out/'FROZEN.json').write_text(json.dumps(frozen,indent=2))
 original.train(cfg,out)
def queue():
 O.mkdir(parents=True,exist_ok=True);tasks=[(d,v,s) for d in ['public','reference','to_asap7'] for v in ['numerical_gate','no_agreement'] for s in range(3)]
 def run(t):
  name='%s_%s_s%d'%t;out=O/name
  if (out/'COMPLETED.json').exists():return dict(task=name,status='reused')
  with (O/(name+'.log')).open('x') as f:
   p=subprocess.run([sys.executable,__file__,'--domain',t[0],'--variant',t[1],'--seed',str(t[2])],stdout=f,stderr=subprocess.STDOUT,timeout=10800)
  print(name,p.returncode,flush=True);return dict(task=name,exit_code=p.returncode)
 start=time.time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rs=list(pool.map(run,tasks))
 (O/'queue_completed.json').write_text(json.dumps(dict(tasks=rs,wall_s=time.time()-start),indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--domain');a.add_argument('--variant');a.add_argument('--seed',type=int);a.add_argument('--queue',action='store_true');v=a.parse_args()
 if v.queue:queue()
 else:train(v.domain,v.variant,v.seed)
