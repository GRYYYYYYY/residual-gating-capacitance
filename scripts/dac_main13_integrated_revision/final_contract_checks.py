"""Artifact-level native and source-access checks; no new performance selection."""
from pathlib import Path
import sys,json,csv,collections,hashlib,time
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R));sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
import evaluate as old
from native_sparse import build_inputs,parse_dump
from unified.queries import query_table
O=R/'results/dac_main13_integrated_revision/main13_20261117';rows=[];poison=[];sealing=[];P=old.Predictors('public',learned=False)
for folder in sorted((O/'native/inputs').glob('*/*')):
 support=json.loads((folder/'support.json').read_text());byctx={s['context_key']:s for s in support};ready=json.loads((folder/'ready.json').read_text());knots,slots=parse_dump(folder/'inventory/slots.tsv');chosen={s['key']:s for s in slots if s['eligible'] and s['context'] in byctx}
 assert len(chosen)==ready['eligible_slots'];scale=2000 if folder.parent.name=='gf180' else 1000;factor=scale/1000
 b,seed=map(int,folder.name.replace('B','').replace('s','').split('_'));start=time.perf_counter();clean,released,_,_=build_inputs(folder.parent.name,b,seed);wall=time.perf_counter()-start
 assert clean==(folder/'sparse.rules').read_text() and released==support
 sealing.append(dict(platform=folder.parent.name,budget=b,seed=seed,input_sealing_wall_s=wall,scope='isolated evaluator-owned input release; same frozen inputs; warm/uncontrolled file cache; no prediction, inventory or extraction'))
 for method in ['mli_native','binary_native','full_native']:
  vals={a[0]:np.array([float(a[1]),float(a[2])]) for a in (l.split() for l in (folder/(method+'.tsv')).read_text().splitlines())};assert set(vals)==set(chosen)
  for ctx,s in byctx.items():
   seq=sorted([k for k in vals if chosen[k]['context']==ctx],key=lambda k:int(k.split('|')[8]));ys=np.array(P.scales['targets'][s['context']['family']])/factor
   v=np.array([vals[k] for k in seq]);assert np.isfinite(v).all() and (v>=0).all()
   protected={int(np.floor(x[1]*scale+.5))//4 for x in s['S_coordinates']};assert all(int(k.split('|')[7]) not in protected for k in seq)
   # Only adjacent initialized canonical slots; intervening observed bins excluded.
   diffs=np.array([abs(vals[b]-vals[a])/ys for a,b in zip(seq,seq[1:]) if int(b.split('|')[7])-int(a.split('|')[7])==1])
   rows.append(dict(platform=folder.parent.name,setting=folder.name,method=method,table_id=s['table_id'],eligible_slots=len(seq),observed_bins_preserved=True,finite_nonnegative=True,max_adjacent_source_scaled_jump=float(diffs.max()) if diffs.size else '',p99_adjacent_source_scaled_jump=float(np.quantile(diffs,.99)) if diffs.size else '',jumps_above_one_source_scale=int((diffs>1).sum()) if diffs.size else 0,interpretation='descriptive discontinuity diagnostic; no universal monotonicity requirement'))
 # Re-execute prediction on label-poison-derived inputs for the two gate fixtures.
 if folder.parent.name in ['asap7','ihp-sg13g2'] and folder.name=='B4_s11':
  reader=old.read_tables;indices={s['table_id']:set(s['support_indices']) for s in support}
  def poisoned_reader(path):
   ts=reader(path)
   for t in ts:
    if t['table_id'] in indices:
     t['labels']=[[987654.321+component for component in range(len(y))] if i not in indices[t['table_id']] else y for i,y in enumerate(t['labels'])]
   return ts
  old.read_tables=poisoned_reader
  try:clean,ss,_,proof=build_inputs(folder.parent.name,4,11,poison=True)
  finally:old.read_tables=reader
  assert clean==(folder/'sparse.rules').read_text() and ss==support
  for method in ['binary_native','full_native']:
   expected={a[0]:[float(a[1]),float(a[2])] for a in (l.split() for l in (folder/(method+'.tsv')).read_text().splitlines())};regenerated={}
   for s in ss:
    seq=sorted([v for v in chosen.values() if v['context']==s['context_key']],key=lambda a:(int(a['key'].split('|')[8]),a['key']))
    for offset in range(0,len(seq),32):
     batch=seq[offset:offset+32];q=np.array([[s['S_coordinates'][0][0],int(a['key'].split('|')[8])/scale,int(a['key'].split('|')[8])/scale] for a in batch]);g,idx,v,ix=query_table(s['S_coordinates'],s['S_values'],q,s['context']);pred=P(method.split('_')[0],g,idx,v)[ix]/factor
     for slot,p in zip(batch,pred):regenerated[slot['key']]=p.tolist()
   assert regenerated==expected;poison.append(dict(platform=folder.parent.name,method=method,predictions=len(expected),bit_exact=True))
with (O/'physical_behavior.csv').open('w') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
if not (O/'input_sealing_timing.csv').exists():
 with (O/'input_sealing_timing.csv').open('x') as f:w=csv.DictWriter(f,list(sealing[0]));w.writeheader();w.writerows(sealing)
tests=O/'tests';tests.mkdir(exist_ok=True);(tests/'final_contract_checks.json').write_text(json.dumps(dict(status='PASS',all_inputs=24,physical_table_checks=len(rows),poison_prediction_reexecution=poison,observation_protection=True,finite_nonnegative=True,shared_eligible_keys=True,monotonicity='not asserted without geometry/component-specific law',symmetry='native queries retain equal left/right scalar projection; arbitrary asymmetric physical symmetry not validated'),indent=2))
print('contract checks PASS',len(rows),poison)
