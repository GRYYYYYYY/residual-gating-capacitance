"""Read-only failure diagnosis. Does not repair or authorize execution."""
from core import *
from unified.train import sample_episode
import collections
plans=episodes();train=tables('reference','train');groups={i:[t for t in train if t['family']==fam] for i,fam in enumerate(FAMILIES)};lookup={t['table_id']:t for t in train};_,state,_=load('Full',0)
checks=[]
for seed in range(3):
 actual=sample_episode(np.random.default_rng(seed),groups,state['scales'])
 for (fi,e,q,y),ep in zip(actual,plans[seed][0]):
  t=lookup[ep['table_id']];h=ep['H'];other=encode(public_input(t),h,np.asarray(t['labels'])[h],state['scales'])
  fields={k:dict(ordinary_equal=bool(np.array_equal(e[k],other[k])),equal_nan=bool(np.array_equal(e[k],other[k],equal_nan=True)),nan_count=int(np.isnan(e[k]).sum()),shape=list(e[k].shape)) for k in ['features','anchor','gate','delta','valid']}
  checks.append(dict(seed=seed,family_index=fi,table_id=ep['table_id'],query_equal=bool(np.array_equal(q,ep['Q'])),truth_equal=bool(np.array_equal(y,t['labels'])),fields=fields))
counts=collections.Counter();qcounts=[0]*3
for seed,steps in enumerate(plans):
 assert len(steps)==2000
 for step in steps:
  assert len(step)==4
  for ep in step:
   t=lookup[ep['table_id']];h,q=mask(t['coordinates'],ep['protocol'],ep['ratio'],ep['mask_seed']);assert list(h)==ep['H'] and list(q)==ep['Q'];assert len(ep['L'])==ep['B'] and set(ep['L'])<=set(ep['H']) and not set(ep['L'])&set(ep['Q']);qcounts[seed]+=len(q);counts[(len(h),ep['B'],len(q))]+=1
write(OUT/'FAILURE_DIAGNOSIS.json',dict(status='INCONCLUSIVE_IMPLEMENTATION',scientific_endpoints_planned=12,scientific_endpoints_started=0,scientific_endpoints_completed=0,scientific_endpoints_failed=0,preflight_failed_attempts=2,downstream_freeze_failed_attempts=1,permitted_implementation_repair_used=True,training_authorized_to_proceed=False,root_cause='ordinary numpy.array_equal treats identical NaN sentinels in unavailable analytic basis entries as unequal; diagnostic equal_nan check only, no repair or retry',sampler_first_step_checks=checks,all_24000_episode_indices_valid=True,training_query_nodes_per_endpoint_by_seed=qcounts,support_query_counts=[dict(H=h,L=l,Q=q,count=n) for (h,l,q),n in sorted(counts.items())],freeze_status='FROZEN_PLAN exists as a failed freeze attempt; FREEZE_MANIFEST absent, not executable; DATA_MANIFEST never generated because prepare stopped',global_state='COMPLETION_ACCURACY_ONLY'))
print('DIAGNOSIS',all(all(x['equal_nan'] for x in c['fields'].values()) for c in checks),qcounts,flush=True)
