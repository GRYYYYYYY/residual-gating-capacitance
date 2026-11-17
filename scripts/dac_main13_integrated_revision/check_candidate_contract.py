"""Verify archived member-wise gate/candidate algebra without model execution."""
from pathlib import Path
import json,gzip
import numpy as np
O=Path(__file__).resolve().parents[2]/'results/dac_main13_integrated_revision/main13_20261117'
out=[]
for domain in ['public','reference','to_asap7']:
 n=0;norm=0.;algebra=0.;invalid=0.
 with gzip.open(O/f'mechanism/{domain}_candidate_outputs.jsonl.gz','rt') as f:
  for r in map(json.loads,f):
   if 'candidate' not in r:continue
   a=np.asarray(r['anchor']);c=np.asarray(r['candidate']);w=np.asarray(r['weights']);v=np.asarray(r['valid'],bool);wc=np.asarray(r['weighted_correction']);s=np.asarray(r['scale'])
   assert all(np.isfinite(x).all() for x in [a,c,w,wc,s]);assert (w>=0).all() and v[:,0].all()
   norm=max(norm,float(abs(w.sum(1)-1).max(initial=0)));invalid=max(invalid,float(abs(w[~v]).max(initial=0)))
   algebra=max(algebra,float(abs((w*(c-a[:,None,:])-wc)/s).max(initial=0)));n+=1
 assert norm<2e-6 and invalid==0 and algebra<2e-5,(domain,norm,invalid,algebra)
 out.append(dict(domain=domain,member_episodes=n,max_weight_sum_error=norm,max_invalid_weight=invalid,max_source_scaled_weighted_correction_roundoff=algebra))
(O/'tests/candidate_contract.json').write_text(json.dumps(dict(status='PASS',checks=out,interpretation='valid convex weights and weighted-correction algebra; no accuracy guarantee'),indent=2));print('candidate contract PASS',out)
