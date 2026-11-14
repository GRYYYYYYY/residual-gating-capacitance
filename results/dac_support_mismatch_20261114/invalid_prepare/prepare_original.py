from core import *
import subprocess,time,collections
started=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
train=tables('reference','train');confirm=tables('reference','confirmation');val=tables('reference','val')
assert len(train)==16 and {len(t['coordinates']) for t in train}=={153}
assert {t['partition'] for t in train}=={'train'}
assert not set(t['table_id'] for t in train)&set(t['table_id'] for t in confirm)
lineage=[];checks=[]
for a in ('Full','binary'):
 for s in range(3):
  p=source(a,s);model,state,cfg=load(a,s);assert cfg['eta']==0 and cfg['dropout']==0 and cfg['span_weight']==False
  assert 'optimizer' not in state and 'optimizer_state_dict' not in state
  receipt=json.loads((p.parent/'COMPLETED.json').read_text());assert sha(p)==receipt['checkpoint_sha256']
  t=train[0];o,q=mask(t['coordinates'],'mcar',.3,11);y=np.asarray(t['labels']);g=public_input(t)
  pred=predict_table([model],state['scales'],g,o,y[o],basis=names(a))[0]
  poison=dict(t,labels=(y*0+1e15).tolist());pred2=predict_table([model],state['scales'],public_input(poison),o,y[o],basis=names(a))[0]
  assert np.array_equal(pred,pred2)
  if a=='Full':
   ms,sc=load_members([p]);assert np.array_equal(pred,predict_table(ms,sc,g,o,y[o])[0])
  checks.append(dict(architecture=a,seed=s,strict_load=True,hidden_label_poison_equal=True,full_loader_equal=True if a=='Full' else 'strict SimpleControl state, same forward',optimizer_present=False))
  lineage.append(dict(architecture=a,seed=s,path=str(p),sha256=sha(p),source_steps=receipt['steps'],source_config=cfg,source_frozen_sha256=sha(p.parent/'FROZEN.json'),source_receipt_sha256=sha(p.parent/'COMPLETED.json'),source_wall_seconds=receipt['wall_seconds'],successors=[f'{a}_{arm}_s{s}' for arm in ('H','L')]))
write(OUT/'CHECKPOINT_LINEAGE.json',lineage);write(OUT/'PREFLIGHT.json',dict(checks=checks,training_tables=16,validation_tables=len(val),confirmation_tables=len(confirm),preparation_utc=started))
# Reproduce original sampler's RNG order exactly; independent L random stream.
plans=[];counts=collections.Counter();cache={}
groups={i:[t for t in train if t['family']==fam] for i,fam in enumerate(FAMILIES)}
for seed in range(3):
 rng=np.random.default_rng(seed);low=np.random.default_rng(611140+seed);steps=[]
 for step in range(2000):
  eps=[]
  for fi,pool in groups.items():
   processes=sorted({t['process_id'] for t in pool});proc=processes[int(rng.integers(len(processes)))];cand=[t for t in pool if t['process_id']==proc];t=cand[int(rng.integers(len(cand)))];protocols=['mcar','block','extrapolation']+(['width'] if t['width_count']>1 else []);protocol=protocols[int(rng.integers(len(protocols)))];ratio=RATIOS[int(rng.integers(len(RATIOS)))];mseed=int(rng.integers(2**31));h,q=mask(t['coordinates'],protocol,ratio,mseed);b=int(low.choice([4,8,16,32]));key=(t['table_id'],tuple(h))
   if key not in cache:cache[key]=geometry_order(t['coordinates'],h)[:32]
   l=sorted(cache[key][:b]);assert set(l)<=set(h) and not set(q)&set(l)
   eps.append(dict(family_index=fi,table_id=t['table_id'],protocol=protocol,ratio=ratio,mask_seed=mseed,H=h.tolist(),L=l,Q=q.tolist(),B=b));counts[(len(h),b,len(q))]+=1
  steps.append(eps)
 plans.append(steps)
with gzip.open(OUT/'EPISODE_PLAN.json.gz','wt') as f:json.dump(plans,f,separators=(',',':'))
# Verify first sampled original encoded episodes, not merely same table order.
from unified.train import sample_episode
_,state,_=load('Full',0)
for seed in range(3):
 actual=sample_episode(np.random.default_rng(seed),groups,state['scales'])
 for original,ep in zip(actual,plans[seed][0]):
  fi,e,q,y=original;t=next(t for t in train if t['table_id']==ep['table_id']);h=ep['H'];new=encode(public_input(t),h,np.asarray(t['labels'])[h],state['scales'])
  assert np.array_equal(q,ep['Q']) and np.array_equal(y,t['labels'])
  for k in ('features','anchor','gate','delta','valid'):assert np.array_equal(e[k],new[k]),k
# Reuse exact existing fixed-Q, same-S evaluation records (no metric used in plan).
old=ROOT/'results/dac_characterization_20261114/confirmation_reference/records.jsonl.gz'
with gzip.open(old,'rt') as f:rows=[json.loads(x) for x in f]
print('OLD_SCHEMA',list(rows[0]),flush=True)
# Evaluation schema is adapted below only if required before freeze.
write(OUT/'PLAN_COUNTS.json',dict(support_query_counts=[dict(H=h,L=l,Q=q,episodes=n) for (h,l,q),n in sorted(counts.items())],total_episodes=sum(counts.values())))
write(OUT/'DATA_MANIFEST.json',[dict(split=split,table_id=t['table_id'],group=dependency_group(t),family=t['family'],nodes=len(t['coordinates']),content_sha256=hashlib.sha256(json.dumps(t,sort_keys=True).encode()).hexdigest()) for split,ts in [('train',train),('val',val),('confirmation',confirm)] for t in ts])
print('PREPARED',len(plans),flush=True)
