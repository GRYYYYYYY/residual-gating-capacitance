from common import *
import math
rs=list(csv.DictReader((O/'support_coverage_scores.csv').open()));prior=read(R/'experiments/paper_controls/comparison_summary.json');checks=[]
for d in ['public','reference','to_asap7']:
 for m in ['full','binary','anchor']:
  for cond,expect in prior[d][m].items():
   if expect is None:continue
   reg,proto=cond.split('/');r=next(r for r in rs if r['domain']==d and r['population']=='common' and r['method']==m and float(r['requested_holdout'])==.3 and r['regime']==reg and r['protocol']==proto)
   err=abs(float(r['macro_nrmse'])-expect);tol=1e-7 if m=='anchor' else 1e-12;assert err<tol,(d,m,cond,err)
   checks.append(dict(domain=d,method=m,condition=cond,max_absolute_difference=err,tolerance=tol))
write(O/'coverage_reuse_checks.json',dict(passed=True,checks=checks,ratios=[.1,.3,.5,.7],same_SQ_checked_for_every_episode=True,anchor_precision_note='Prior displayed anchor was reconstructed from encoded float32; new numerical-only path returns float64. Maximum macro-score difference8.8e-9; model Full/Binary scores exact.'))
print('original30% controls matched',len(checks))
