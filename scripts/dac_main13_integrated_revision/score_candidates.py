"""Independent reference-reading scorer for sealed frozen candidate diagnostics."""
from pathlib import Path
import json,gzip,csv,collections
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';M=O/'mechanism';cfg=json.loads((R/'configs/paper_models.json').read_text());acc=collections.defaultdict(lambda:np.zeros(8));simple=collections.defaultdict(lambda:np.zeros(7));case_rows=[]
for domain in cfg:
 assert (M/f'{domain}_frozen_completed.json').exists()
 tables={t['table_id']:t for t in map(json.loads,(R/cfg[domain]['cohort']).read_text().splitlines())};anchors={};segments={}
 with gzip.open(M/f'{domain}_candidate_outputs.jsonl.gz','rt') as f,gzip.open(M/f'{domain}_candidate_scores.jsonl.gz','wt') as out:
  for r in map(json.loads,f):
   q=r['query_indices'];truth=np.asarray(tables[r['table_id']]['labels'])[q];ek=(r['table_id'],r['protocol'],r['ratio'],r['mask_seed']);meta={k:r[k] for k in ['domain','table_id','protocol','ratio','mask_seed','member']}
   if 'candidate' in r:
    a=np.array(r['anchor']);c=np.array(r['candidate']);v=np.array(r['valid']);w=np.array(r['weights']);wc=np.array(r['weighted_correction']);seg=np.array(r['segment']);error=c-truth[:,None,:];desired=truth-a;delta=c-a[:,None,:]
    # Only retain the current episode for subsequent simplified-member rows.
    if r['member']==0:anchors.clear();segments.clear()
    anchors[r['member']]=a;segments[r['member']]=seg
    out.write(json.dumps(dict(**meta,query_indices=q,squared_error=(error**2).tolist(),residual_direction_correct=(delta*desired[:,None,:]>=0).tolist(),candidate_better_than_anchor=(abs(error)<abs(desired[:,None,:])).tolist(),valid=v.tolist()),allow_nan=False)+'\n')
    for reg,mask in [('inside',seg!=0),('outside',seg==0)]:
     if not mask.any():continue
     for e in range(c.shape[1]):
      valid=mask&v[:,e]
      for k in range(c.shape[2]):
       key=(domain,reg,r['protocol'],r['ratio'],r['member'],e,k);z=valid
       acc[key]+=[z.sum(),(error[z,e,k]**2).sum(),(desired[z,k]**2).sum(),w[z,e,k].sum(),abs(wc[z,e,k]).sum(),(delta[z,e,k]*desired[z,k]>=0).sum(),(abs(error[z,e,k])<abs(desired[z,k])).sum(),(truth[z,k]**2).sum()]
   else:
    a=anchors[r['member']];seg=segments[r['member']];res=np.array(r['raw_residual']);alpha=np.array(r['alpha']);p=np.array(r['prediction']);desired=truth-a
    for reg,mask in [('inside',seg!=0),('outside',seg==0)]:
     for k in range(truth.shape[1]):
      z=mask
      if not z.any():continue
      key=(domain,reg,r['protocol'],r['ratio'],r['method'],r['member'],k)
      simple[key]+=[z.sum(),(res[z,k]*desired[z,k]<0).sum(),((res[z,k]*desired[z,k]>=0)&(abs(res[z,k])>2*abs(desired[z,k]))).sum(),alpha[z,k].sum(),((p[z,k]-truth[z,k])**2).sum(),(desired[z,k]**2).sum(),((np.maximum(a[z,k]+res[z,k],0)-truth[z,k])**2).sum()]
 print('SCORED',domain,flush=True)
rows=[]
for key,z in sorted(acc.items()):
 domain,reg,proto,ratio,member,e,k=key
 rows.append(dict(domain=domain,regime=reg,protocol=proto,ratio=ratio,member=member,candidate_index=e,component=k,valid_query_occurrences=int(z[0]),candidate_SSE=z[1],anchor_SSE=z[2],mean_weight=z[3]/z[0] if z[0] else '',sum_abs_weighted_correction=z[4],correct_direction_fraction=z[5]/z[0] if z[0] else '',better_than_anchor_fraction=z[6]/z[0] if z[0] else '',reference_energy=z[7],relative_SSE_to_anchor=z[1]/z[2] if z[2]>0 else ''))
with (O/'mechanism_candidate_metrics.csv').open('w') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
rows=[]
for key,z in sorted(simple.items()):
 domain,reg,proto,ratio,method,member,k=key
 rows.append(dict(domain=domain,regime=reg,protocol=proto,ratio=ratio,method=method,member=member,component=k,query_occurrences=int(z[0]),wrong_direction_fraction=z[1]/z[0],overcorrecting_fraction=z[2]/z[0],mean_alpha=z[3]/z[0],prediction_SSE=z[4],anchor_SSE=z[5],own_ungated_candidate_SSE=z[6]))
with (O/'mechanism_simplified_diagnostics.csv').open('w') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
(M/'candidate_scoring_completed.json').write_text(json.dumps(dict(status='PASS',independent_scorer=__file__,labels_access='read only after frozen candidate files and completion receipts exist; no predictor imported',candidate_names=json.loads((M/'public_frozen_completed.json').read_text())['candidate_order'],records=len(rows)),indent=2))
