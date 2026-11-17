"""Identity-align old census Q stream and full-support injection traces."""
from pathlib import Path
import csv,json,itertools
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';rows=list(csv.DictReader((O/'coverage_accounting.csv').open()));checks=[]
for r in rows:
 case=r['case'];old=R/'results/layout_offgrid_20261115/native'/case/'trace.tsv';new=R/'results/pex_kernel_revision/validation'/case/'disabled/0/getters.tsv';n=0;unresolved=0
 with old.open() as f,new.open() as g:
  q=(l.rstrip().split('\t') for l in f if l.startswith('Q\t'))
  for a,line in itertools.zip_longest(q,g):
   assert a is not None and line is not None,case;b=line.rstrip().split('\t');ctx=b[0].split('|')
   assert [int(a[i]) for i in [5,7,8]]==[int(b[1]),int(b[2]),int(b[3])],(case,n)
   if len(ctx)>=7:assert [int(a[2]),int(a[6])]==[int(ctx[3]),int(ctx[6])],(case,n)
   else:unresolved+=1
   assert [float(a[9]),float(a[10])]==[float(b[4]),float(b[5])],(case,n)
   n+=1
 assert n==int(r['finite_getter_calls']);checks.append(dict(case=case,aligned_calls=n,order_geometry_and_values_exact=True,unresolved_context_calls=unresolved))
 r['changed_fraction_all_matched_getters']=int(r['changed_returns'])/int(r['all_two_getter_calls']);r['trace_identity_alignment']='PASS'
 print('ALIGNED',case,n,flush=True)
with (O/'coverage_accounting.csv').open('w') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
all_calls=sum(int(r['all_two_getter_calls']) for r in rows);changed=sum(int(r['changed_returns']) for r in rows);finite=sum(int(r['finite_getter_calls']) for r in rows)
(O/'coverage_trace_alignment.json').write_text(json.dumps(dict(status='PASS',checks=checks,all_calls=all_calls,finite_calls=finite,changed_returns=changed,changed_fraction_all=changed/all_calls,changed_fraction_finite=changed/finite,interpretation='Numerical changes only. Fringe getter unchanged in compute hook. No physical improvement fraction established.'),indent=2))
