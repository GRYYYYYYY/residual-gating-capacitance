"""Cluster-paired fixed-budget contrasts, preserving pooled support-seed aggregation."""
from pathlib import Path
import csv,gzip,json,collections
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';rows=[]
for domain in ['public','reference','to_asap7']:
 with gzip.open(R/f'results/dac_characterization_20261114/confirmation_{domain}/records.jsonl.gz','rt') as f:rs=[r for r in map(json.loads,f) if r.get('status')=='ok' and r['strategy']=='farthest' and r['method'] in ['full','binary','gp','mlp_adapt']]
 for budget in sorted({r['budget'] for r in rs}):
  rr=[r for r in rs if r['budget']==budget];groups=sorted({r['dependency_group'] for r in rr});strata=sorted({(r['process_id'],r['family'],k) for r in rr for k in range(len(r['squared_error']))});methods=['full','binary','gp','mlp_adapt'];a=np.zeros((len(groups),len(strata),4,2))
  gi={g:i for i,g in enumerate(groups)};si={g:i for i,g in enumerate(strata)}
  for r in rr:
   for k,(e,y) in enumerate(zip(r['squared_error'],r['squared_truth'])):a[gi[r['dependency_group']],si[r['process_id'],r['family'],k],methods.index(r['method'])]+=[e,y]
  def score(x):
   with np.errstate(invalid='ignore',divide='ignore'):v=np.where(x[...,1]>0,np.sqrt(x[...,0]/x[...,1]),np.nan)
   return np.nanmean(v,axis=-2)
  point=score(a.sum(0));w=np.zeros((1000,len(groups)));rng=np.random.default_rng(20261117)
  for proc in sorted({r['process_id'] for r in rr}):
   ids=sorted({gi[r['dependency_group']] for r in rr if r['process_id']==proc});w[:,ids]=rng.multinomial(len(ids),np.ones(len(ids))/len(ids),1000)
  boot=score(np.einsum('bg,gsmk->bsmk',w,a))
  for i,m in enumerate(methods[1:],1):
   lo,hi=np.quantile(boot[:,0]-boot[:,i],[.025,.975]);rows.append(dict(domain=domain,budget=budget,comparison='full-minus-'+m,full_nrmse=point[0],control_nrmse=point[i],difference=point[0]-point[i],ci_low=lo,ci_high=hi,independent_groups=len(groups),unit='public split group or physical process-layer; all support seeds pooled within group',uncertainty='descriptive; very few clusters' if len(groups)<10 else 'paired cluster bootstrap'))
with (O/'fixed_budget_paired_comparisons.csv').open('w') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
print('paired comparisons',len(rows))
