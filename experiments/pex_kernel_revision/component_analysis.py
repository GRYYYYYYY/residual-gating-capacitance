"""Decompose completed physical outputs and raw/effective geometry; no inference."""
from common import *
import gzip,collections
import numpy as np
rs=[json.loads(l) for l in gzip.open(O/'physical_predictions.jsonl.gz','rt')];slots=[json.loads(l) for l in gzip.open(O/'physical_slots.jsonl.gz','rt')];ss={(s['table_id'],s['width_index'],s['slot']) for s in slots};plan={q['query_id']:q for q in read(R/'results/layout_offgrid_20261115/reference_plan.json')['queries']};metrics=[];geometry=[]
for m in sorted({r['method'] for r in rs}):
 for fam in sorted({r['family'] for r in rs}):
  rr=[r for r in rs if r['method']==m and r['family']==fam];y=np.array([r['reference'] for r in rr]);p=np.array([r['prediction'] for r in rr]);e=p-y
  for j,name in enumerate(rr[0]['components']):
   sy=float((y[:,j]**2).sum());metrics.append(dict(method=m,family=fam,component=name,queries=len(rr),unit='F/m',nrmse=float(np.sqrt((e[:,j]**2).sum()/sy)) if sy>0 else None,p95_absolute=float(np.quantile(abs(e[:,j]),.95)),p99_absolute=float(np.quantile(abs(e[:,j]),.99)),max_absolute=float(max(abs(e[:,j])))))
for r in rs:
 if r['method']!='openrcx_kernel':continue
 q=plan[r['query_id']];a=r['native_meta'];key=(r['table_id'],a['width_index'],a['slot']);geometry.append(dict(query_id=r['query_id'],table_id=r['table_id'],raw_width_um=q['coordinates'][0],raw_spacing_um=q['coordinates'][1],mapped_width_um=a['mapped_width_um'],represented_spacing_um=a['effective_separation']/1000.,native_route=a['path'],injected_slot=key in ss and a['path']=='compute',slot=a['slot'],width_delta_um=a['mapped_width_um']-q['coordinates'][0],spacing_delta_um=a['effective_separation']/1000.-q['coordinates'][1]))
csvwrite(O/'physical_component_metrics.csv',metrics);csvwrite(O/'physical_geometry_effects.csv',geometry)
write(O/'physical_mapping_contract.json',dict(query_geometries=71,source_geometry_modified=False,characterization_values_modified=False,integer_encoding='round positive um*1000 to pinned integer rule coordinates; native width modulo4 and distance unit4',projection='kernel independently evaluates each declared scalar: ground, summed lateral, diagonal. The harness fields are storage channels, not an assertion of native fringe/coupling/resistance physical equivalence.',native_direct_vs_ideal='same native width map; ideal removes distance integer/grid conversion only',learned_direct_vs_populated='changes Q-set/batching and native mapping jointly; not labeled an isolated quantization effect',injected_query_count=sum(r['injected_slot'] for r in geometry),distinct_effective_keys=len({(r['table_id'],r['mapped_width_um'],r['represented_spacing_um']) for r in geometry})))

# Reuse recorded final-stage training costs without treating missing costs as zero.
from summarize import table
cost=read(R/'results/runtime_accuracy_20261115/supplied_input_costs.json');tr=collections.defaultdict(list)
for r in cost['training_receipts']:tr[r['setting'],r['method']].append(r['wall_seconds'])
rows=[]
for domain,label in [('public','Public'),('reference','FEM'),('to_asap7','Transfer')]:
 rows.append([label]+[f'{sum(tr[domain,m]):.1f}' if len(tr[domain,m])==3 else '--' for m in ['full','binary','residual','mlp','cnp','attentioncap']])
table('source_training_costs',['Setting','Full','Binary','Ungated','MLP','CNP','Adapted AC'],rows,'lrrrrrr')
write(O/'supplied_cost_provenance.json',dict(input='results/runtime_accuracy_20261115/supplied_input_costs.json',sha256=sha(R/'results/runtime_accuracy_20261115/supplied_input_costs.json'),scope='sum of three recorded final-stage wall seconds, not parallel elapsed or complete pipeline cost; missing receipts are unavailable, never zero',no_new_training=True))
