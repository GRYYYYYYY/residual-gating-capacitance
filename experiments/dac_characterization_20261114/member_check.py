"""Training-seed sensitivity at preregistered data seed 11; no selection."""
import gzip,time
from common import *
from evaluate import trajectory
from pdkcap.metrics import record,summarize
from unified.score import predict_table
import torch
D=ROOT/'results/dac_characterization_20261114/member_sensitivity';D.mkdir(exist_ok=False);torch.set_num_threads(1);start=time.perf_counter();rows=[]
for s in MODELS:
 fulls,sc=full(s);models=controls(s,sc)|{'full':fulls}
 for t in tables(s,'confirmation'):
  if len(t['coordinates'])<4:continue
  c,q,snaps=trajectory(t,11,'farthest')
  for o,v,_,_ in snaps:
   for kind,ms in models.items():
    for seed,m in enumerate(ms):
     p=predict_table([m],sc,public_input(t),o,v,**({} if kind=='full' else {'basis':('linear',)}))[0]
     rows.append(record(t,np.asarray(t['labels'])[q],p[q],setting=s,method=kind,training_seed=seed,data_seed=11,budget=len(o)))
with gzip.open(D/'records.jsonl.gz','xt') as f:
 for r in rows:f.write(json.dumps(r)+'\n')
summary=[]
for s in MODELS:
 for kind in ('full','residual','binary'):
  for b in sorted({r['budget'] for r in rows if r['setting']==s}):
   for seed in (0,1,2):summary.append(dict(setting=s,method=kind,budget=b,training_seed=seed,nrmse=summarize([r for r in rows if r['setting']==s and r['method']==kind and r['budget']==b and r['training_seed']==seed])['nrmse']))
write(D/'summary.json',summary);write(D/'COMPLETED.json',dict(records=len(rows),seconds=time.perf_counter()-start,scope='descriptive training seeds; fixed data seed11; no tuning'))
