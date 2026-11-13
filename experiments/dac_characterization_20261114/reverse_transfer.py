"""Prefrozen reverse-direction direct-MLP control; no full-gate retraining."""
import json,time,gzip
from common import *
from learning import Net,feature,prediction,tensor
from evaluate import trajectory
from pdkcap.model import fit_scales
from pdkcap.metrics import record,summarize
import torch
from torch import nn
D=ROOT/'results/dac_characterization_20261114/reverse_transfer';D.mkdir(exist_ok=False)
train=[t for t in tables('reference','train') if t['process_id']=='asap7'];val=[t for t in tables('reference','val') if t['process_id']=='asap7'];test=[t for t in tables('reference','confirmation') if t['process_id']=='freepdk15']
assert (len(train),len(val),len(test))==(8,12,8)
sc=fit_scales(train);torch.set_num_threads(1)
write(D/'FROZEN.json',dict(source='asap7',target='freepdk15',train_ids=[t['table_id'] for t in train],val_ids=[t['table_id'] for t in val],confirmation_ids=[t['table_id'] for t in test],scales=sc,lr_candidates=[.001,.0003],adapt_steps_candidates=[0,50,200],steps=3000,seeds=[0,1,2],source_hash=sha(__file__)))
def fit(lr,seed):
 torch.manual_seed(seed);rng=np.random.default_rng(seed);m=Net('mlp',feature(train[0],sc).shape[1],3);opt=torch.optim.AdamW(m.parameters(),lr=lr,weight_decay=1e-4)
 data=[(tensor(feature(t,sc)),tensor(np.asarray(t['labels'])/sc['targets'][t['family']])) for t in train];start=time.perf_counter()
 for step in range(3000):
  opt.zero_grad();loss=0
  for family in ('OVER','UNDER','OVERUNDER','DIAGUNDER'):
   i=int(rng.choice([i for i,t in enumerate(train) if t['family']==family]));x,y=data[i];loss+=nn.functional.huber_loss(m(x),y)/4
  loss.backward();nn.utils.clip_grad_norm_(m.parameters(),1.);opt.step()
 m.eval();p=D/f'mlp_lr{lr:g}_s{seed}.pt';torch.save(m.state_dict(),p);write(p.with_suffix('.json'),dict(wall_seconds=time.perf_counter()-start,checkpoint_sha256=sha(p),seed=seed,lr=lr));return m
choices=[];candidates={}
for lr in (.001,.0003):
 m=fit(lr,0);candidates[lr]=m
 for n in (0,50,200):
  rows=[]
  for t in val:
   _,q,snaps=trajectory(t,11,'farthest')
   for o,v,_,_ in snaps:
    p=prediction(m,sc,public_input(t),o,v,n);rows.append(record(t,np.asarray(t['labels'])[q],p[q]))
  choices.append(dict(lr=lr,adapt_steps=n,score=summarize(rows)['nrmse']))
best=min(choices,key=lambda x:(x['score'],x['adapt_steps']));write(D/'selection.json',best|dict(candidates=choices));members=[candidates[best['lr']]]+[fit(best['lr'],s) for s in (1,2)]
rows=[]
with gzip.open(D/'records.jsonl.gz','xt') as f:
 for t in test:
  for seed in (11,29,47):
   c,q,snaps=trajectory(t,seed,'farthest')
   for o,v,_,_ in snaps:
    for name,n in [('mlp_zero',0),('mlp_adapt',best['adapt_steps'])]:
     start=time.perf_counter();p=np.mean([prediction(m,sc,public_input(t),o,v,n) for m in members],0)
     r=record(t,np.asarray(t['labels'])[q],p[q],setting='to_freepdk15',method=name,budget=len(o),data_seed=seed,strategy='farthest',status='ok',query_indices=q.tolist(),support_indices=o.tolist(),unique_reference_queries=len(o) if n else 0,prediction_and_adaptation_wall_seconds=time.perf_counter()-start)
     f.write(json.dumps(r)+'\n');rows.append(r)
write(D/'COMPLETED.json',dict(records=len(rows),selection=best,nrmse={m:summarize([r for r in rows if r['method']==m])['nrmse'] for m in ('mlp_zero','mlp_adapt')}))
