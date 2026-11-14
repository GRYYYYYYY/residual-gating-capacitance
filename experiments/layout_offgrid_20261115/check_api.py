import sys,json,time
from pathlib import Path
import numpy as np,torch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
from common import full,controls,tables,public_input
from unified.score import predict_table
from unified.queries import predict_queries,query_table
torch.set_num_threads(1);out=[]
for setting in ['public','reference']:
 t=tables(setting,'val')[0];m,scales=full(setting);ct=controls(setting,scales)
 x=np.array(t['coordinates']);y=np.array(t['labels']);o=np.arange(0,len(x),2);qi=np.setdiff1d(np.arange(len(x)),o);q=x[qi];ctx=public_input(t);ctx.pop('coordinates')
 for method,members,basis in [('full',m,None),('binary',ct['binary'],['linear'])]:
  pol={} if basis is None else dict(basis=basis)
  ref=predict_table(members,scales,t,o,y[o],**({} if basis is None else dict(basis=basis)))[0][qi]
  parity=predict_queries(x[o],y[o],q,ctx,(members,scales),dict(pol,candidate_order=x.tolist()))
  assert np.array_equal(ref,parity)
  # Independent development queries: genuine new coordinates, labels unused.
  dev=(x[:-1]+x[1:])/2;dev=np.unique(dev,axis=0)[:32]
  t0=time.perf_counter();single=predict_queries(x[o],y[o],dev,ctx,(members,scales),dict(pol,batch_size=1))
  small=predict_queries(x[o],y[o],dev,ctx,(members,scales),dict(pol,batch_size=8))
  large=predict_queries(x[o],y[o],dev,ctx,(members,scales),dict(pol,batch_size=32))
  perm=predict_queries(x[o],y[o],dev[::-1],ctx,(members,scales),dict(pol,batch_size=32))[::-1]
  support=predict_queries(x[o],y[o],x[o],ctx,(members,scales),pol);assert np.array_equal(support,y[o])
  union=query_table(x[o],y[o],dev,ctx)[0]['coordinates']
  raw=predict_queries(x[o],y[o],dev,ctx,(members,scales),dict(pol,candidate_order=union))
  rawperm=predict_queries(x[o],y[o],dev,ctx,(members,scales),dict(pol,candidate_order=union[::-1]))
  rawdiff=float(np.max(abs(raw-rawperm)/np.array(scales['targets'][t['family']])))
  # Record raw order sensitivity; the main protocol fixes canonical order.
  extra=(x[:min(8,len(x)-1)]*0.25+x[1:min(9,len(x))]*0.75)
  augmented=np.vstack([dev,extra]);aug=predict_queries(x[o],y[o],augmented,ctx,(members,scales),dict(pol,batch_size=len(augmented)))[:len(dev)]
  out.append(dict(setting=setting,method=method,fixed_grid_bit_exact=True,support_bit_exact=True,development_queries=len(dev),single_large_scaled_max=float(np.max(abs(single-large)/np.array(scales['targets'][t['family']]))),small_large_scaled_max=float(np.max(abs(small-large)/np.array(scales['targets'][t['family']]))),canonical_input_reorder_max=float(np.max(abs(perm-large))),raw_token_permutation_scaled_max=rawdiff,extra_unlabelled_queries_scaled_max=float(np.max(abs(aug-large)/np.array(scales['targets'][t['family']]))),wall_s=time.perf_counter()-t0))
  print(out[-1],flush=True)
(R/'results/layout_offgrid_20261115/api_checks.json').write_text(json.dumps(out,indent=2))
