"""All fixed final endpoints and source checkpoints, no intermediate selection."""
from core import *
import csv,time
plan=endpoint_gate();evals=json.loads((OUT/'EVALUATION_PLAN.json').read_text());ts={t['table_id']:t for t in verified_tables('confirmation')};models={}
for a in plan['architectures']:
 for seed in plan['seeds']:
  for arm in ['0','H','L']:
   path=source(a,seed) if arm=='0' else OUT/'checkpoints'/f'{a}_{arm}_s{seed}'/'checkpoint.pt'
   m,state,cfg=load(a,seed,path);models[(a,arm,seed)]=(m,state)
rows=[];timings=[]
with gzip.open(OUT/'PREDICTIONS.jsonl.gz','xt') as raw:
 for e in evals:
  t=ts[e['table_id']];y=np.asarray(t['labels'],float);o=e['S'];q=e['Q'];g=public_input(t)
  for a in plan['architectures']:
   state=models[(a,'0',0)][1];sc=state['scales'];start=time.process_time();enc=encode(g,o,y[o],sc,names=names(a));batch=stack([enc]);enc_cpu=time.process_time()-start
   for arm in ['0','H','L']:
    for seed in plan['seeds']:
     m,state=models[(a,arm,seed)];assert sc==state['scales'];start=time.process_time();wall=time.perf_counter()
     with torch.inference_mode():
      p=m(batch['features'],batch['anchor'],batch['gate'],batch['delta'],batch['valid'],padding=batch['padding'],clamp_lower=batch['lower'],clamp_upper=batch['upper'],inside=batch['inside'])[0,:enc['n']].numpy()*np.asarray(enc['scales'])
     forward_cpu=time.process_time()-start;forward_wall=time.perf_counter()-wall;p[o]=y[o];assert np.isfinite(p).all()
     meta=dict(cell=e['cell'],cohort=e['cohort'],architecture=a,arm=arm,train_seed=seed,table_id=t['table_id'],group=dependency_group(t),process=t['process_id'],family=t['family'],budget=e['budget'],data_seed=e['data_seed'],protocol=e['protocol'],query_count=len(q),unit=t['units'],status='ok')
     raw.write(json.dumps(dict(**meta,prediction=p.tolist(),truth_Q=y[q].tolist(),Q=q,S=o))+'\n')
     ae=abs(p[q]-y[q]);se=((p[q]-y[q])**2).sum(0);sy=(y[q]**2).sum(0)
     for j,target in enumerate(t['target_names']):rows.append(dict(**meta,component=target,component_index=j,squared_error=float(se[j]),squared_truth=float(sy[j]),absolute_error=float(ae[:,j].sum()),nrmse=float(np.sqrt(se[j]/sy[j])) if sy[j]>0 else '',p95_absolute=float(np.quantile(ae[:,j],.95)),p99_absolute=float(np.quantile(ae[:,j],.99))))
     timings.append(dict(**meta,encoding_cpu_shared_per_arch_cell_s=enc_cpu,forward_cpu_s=forward_cpu,forward_wall_s=forward_wall,encoding_reuse_count=9))
  if e['cell']%32==0:print('EVALUATED',e['cell'],flush=True)
for name,data in [('EVALUATION_CELLS.csv',rows),('PREDICTION_TIMING.csv',timings)]:
 with (OUT/name).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
write(OUT/'EVALUATION_COMPLETED.json',dict(cells=len(evals),model_versions=len(models),component_rows=len(rows),failure_count=0,manifest=sha(OUT/'FREEZE_MANIFEST.json')))
