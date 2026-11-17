"""Fixed-S/slot query-set, ordering, chunk, duplicate and padding diagnostics."""
from pathlib import Path
import sys,json,csv
import numpy as np,torch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R));sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
import evaluate as old
from unified.queries import query_table
from unified.score import predict_table
from unified.episodes import encode,stack
from mechanism import call
O=R/'results/dac_main13_integrated_revision/main13_20261117';torch.set_num_threads(1)
def main():
 rows=[];tol=8*np.finfo(np.float32).eps
 for domain in ['public','reference','to_asap7']:
  P=old.Predictors(domain,learned=False);t=max(old.tables(domain,'confirmation'),key=lambda t:len(t['coordinates']));x=np.array(t['coordinates']);y=np.array(t['labels']);o,q=old.mask(x,'mcar',.5,11) if hasattr(old,'mask') else (None,None)
  if o is None:
   from pdkcap.sampling import mask
   o,q=mask(x,'mcar',.5,11)
  target=x[q[len(q)//2]];truth=y[q[len(q)//2]];ys=np.array(P.scales['targets'][t['family']]);public=old.public_input(t);public.pop('coordinates')
  companions=[a for a in x[q] if not np.array_equal(a,target)]
  # Coordinate-only extra companions; no extra observations or query labels.
  j=1
  while len(companions)<63:
   a=x[0]+(x[-1]-x[0])*(j/67);j+=1
   if not np.array_equal(a,target) and not any(np.array_equal(a,z) for z in companions):companions.append(a)
  c=np.array(companions);queries={'Q1':target[None],'Q8':np.vstack([target,c[:7]]),'Q32':np.vstack([target,c[:31]]),'Q32_other':np.vstack([target,c[31:62]]),'permutation':np.vstack([target,c[:31]])[::-1],'duplicate':np.vstack([target,c[:31],target]),'chunk_boundary':np.vstack([c[31:62],target])}
  for method in ['full','binary','residual']:
   members=P.members if method=='full' else P.control[method];basis=old.CLASSICAL if hasattr(old,'CLASSICAL') else None;preds={};encoded={}
   for name,coords in queries.items():
    g,idx,v,ix=query_table(x[o],y[o],coords,public);args={} if method=='full' else {'basis':('linear',)}
    p=predict_table(members,P.scales,g,idx,v,**args)[0];where=np.flatnonzero(np.all(coords==target,axis=1))[0];preds[name]=p[ix[where]]
    assert np.isfinite(p).all() and (p>=0).all() and np.array_equal(p[idx],v)
    if name=='Q32':encoded[name]=(g,idx,v,ix,where)
   # Same token order, explicit padding via a second, longer batch item.
   g,idx,v,ix,where=encoded['Q32'];e=encode(g,idx,v,P.scales,**({} if method=='full' else {'names':('linear',)}));g2,o2,v2,ix2=query_table(x[o],y[o],np.vstack([target,c[:63]]),public);e2=encode(g2,o2,v2,P.scales,**({} if method=='full' else {'names':('linear',)}));b=stack([e,e2])
   with torch.inference_mode():preds['padding']=np.mean([call(m,b)[0,ix[where]].numpy()*ys for m in members],0)
   for name,p in preds.items():
    ref=preds['Q32'] if name in ['permutation','duplicate','padding'] else preds['Q1'];delta=p-ref
    rows.append(dict(domain=domain,table_id=t['table_id'],method=method,case=name,comparison_to='Q32' if name in ['permutation','duplicate','padding'] else 'Q1',support=len(o),absolute_change=float(abs(delta).max()),source_scaled_change=float((abs(delta)/ys).max()),source_scaled_reference_error=float((abs(p-truth)/ys).max()),source_scaled_error_change=float(((abs(p-truth)-abs(ref-truth))/ys).max()),above_scale_tolerance=bool((abs(delta)/ys>tol).any()),prediction=json.dumps(p.tolist()),truth=json.dumps(truth.tolist()),units=t['units']))
 with (O/'query_batching.csv').open('w') as f:w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
 (O/'query_batching_tests.json').write_text(json.dumps(dict(tolerance_source_scaled=tol,observations_exact=True,finite_nonnegative=True,case_selection='longest confirmation table per domain, fixed random .5 seed11 support and middle query; deterministic, no outcome selection',tests=rows),indent=2))
 print('max scaled changes',[(c,max(r['source_scaled_change'] for r in rows if r['case']==c)) for c in queries])
if __name__=='__main__':main()
