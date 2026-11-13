"""Validation-only component cost measurement, not an end-to-end speed claim."""
import time,csv
from common import *
from evaluate import population
from unified.episodes import encode,stack
from unified.basis import CLASSICAL
import torch
rows=[];torch.set_num_threads(1)
for s in MODELS:
 ms,sc=full(s);t=tables(s,'val')[0];g=public_input(t)
 start=time.perf_counter();c,q,initial=population(g,11);population_s=time.perf_counter()-start
 from pdkcap.sampling import geometry_order
 order=geometry_order(t['coordinates'],c)
 for b in (4,8):
  o=np.array(sorted(order[:b]));v=np.asarray(t['labels'])[o]
  for name,basis in [('full',CLASSICAL),('pruned',('linear',))]:
   start=time.perf_counter();enc=encode(g,o,v,sc,basis);encoding=time.perf_counter()-start;start=time.perf_counter();batch=stack([enc]);packing=time.perf_counter()-start;start=time.perf_counter()
   with torch.inference_mode():
    for m in ms:m(batch['features'],batch['anchor'],batch['gate'],batch['delta'],batch['valid'],padding=batch['padding'],clamp_lower=batch['lower'],clamp_upper=batch['upper'],inside=batch['inside'])
   rows.append(dict(setting=s,method=name,budget=b,table_id=t['table_id'],population_initialization_seconds=population_s,support_and_branch_encoding_seconds=encoding,batch_packing_seconds=packing,ensemble_forward_seconds=time.perf_counter()-start,scope='one validation table; no model-load cost; no amortization assumption'))
p=ROOT/'results/dac_characterization_20261114/component_runtime_profile.csv'
with p.open('x') as f:w=csv.DictWriter(f,rows[0]);w.writeheader();w.writerows(rows)
print('component profiles',len(rows))
