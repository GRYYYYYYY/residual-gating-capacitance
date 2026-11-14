"""Frozen same-S/Q comparisons. Native agreement and direct FEM are separate."""
import sys,json,time,hashlib,collections,copy,csv
from pathlib import Path
import numpy as np,torch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
from common import public_input,sha
import importlib.util
_spec=importlib.util.spec_from_file_location("dac_fixed_predictors",R/"experiments/dac_characterization_20261114/evaluate.py")
_mod=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_mod)
Predictors=_mod.Predictors
from unified.queries import query_table
from pdkcap.reference_dataset import components
from pdkcap.solver import diagnose
O=R/'results/layout_offgrid_20261115';OLD=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/pdkcap-v0/runs/reference_full_v2')
METHODS=['cmi','anchor','affine','gp','residual','binary','full','mlp_adapt','cnp']
def frozen_predict(t,qs,setting,outname):
 p=Predictors(setting,json.loads((R/f'experiments/dac_characterization_20261114/selected_{setting}.json').read_text()))
 x=np.array(t['coordinates']);v=np.array(t['labels']);qs=sorted(qs,key=lambda q:q['geometry_hash']);rows=[]
 for start in range(0,len(qs),32):
  batch=qs[start:start+32];q=np.array([r['coordinates'] for r in batch]);g,o,y,ix=query_table(x,v,q,{k:val for k,val in public_input(t).items() if k!='coordinates'})
  for method in METHODS:
   wall=time.perf_counter();cpu=time.process_time()
   try:pred=p(method,g,o,y)[ix];status='ok';failure=None
   except Exception as e:pred=None;status='failed';failure=repr(e)
   cost=dict(cpu_s=time.process_time()-cpu,wall_s=time.perf_counter()-wall)
   for j,rr in enumerate(batch):
    rows.append(dict(query_id=rr['query_id'],geometry_hash=rr['geometry_hash'],table_id=t['table_id'],process=t['process_id'],family=t['family'],method=method,status=status,failure=failure,prediction=None if pred is None else pred[j].tolist(),reference=rr.get('reference'),reference_kind=rr['reference_kind'],convergence_status=rr.get('convergence_status'),reference_uncertainty=rr.get('reference_uncertainty'),component=t['target_names'],unit=t['units'],S_hash=hashlib.sha256(json.dumps([t['coordinates'],t['labels']],sort_keys=True).encode()).hexdigest(),occurrence_count=rr['occurrence_count'],sampling_probability=rr['sampling_probability'],design_counts=rr['design_counts'],query_class=rr['query_class'],mapping_level=rr['mapping_level'],query_batch_policy='all S + hash-sorted Q chunks32',batch_id=f'{outname}:{t["table_id"]}:{start}',batch_cost=cost))
 return rows

def public_replay():
 supp=json.loads((O/'native_supports.json').read_text());records=[json.loads(l) for l in (O/'query_manifest.jsonl').read_text().splitlines()]
 groups=collections.defaultdict(dict)
 for r in records:
  t=supp.get(r['rule_key'])
  if t is None or t['partition']!='holdout' or len(t['coordinates'])<4 or r['call_type']!='Q' or not r['query_class'].startswith('off_grid'):continue
  g=groups[t['table_id']]
  if r['geometry_hash'] not in g:
   g[r['geometry_hash']]=dict(r,coordinates=r['raw_coordinates'],reference=[z*(r['coordinate_scale']/1000) for z in r['native_prediction']],reference_kind='native_evaluator_agreement_not_physical_truth',design_counts={})
   g[r['geometry_hash']]['occurrence_count']=0
  q=g[r['geometry_hash']];q['occurrence_count']+=r['occurrence_count'];q['design_counts'][r['design']]=q['design_counts'].get(r['design'],0)+r['occurrence_count']
 selected=[]
 for tid,g in sorted(groups.items()):
  qs=sorted(g.values(),key=lambda r:hashlib.sha256(('20261115'+r['geometry_hash']).encode()).hexdigest())
  for q in qs[:max(1,512//max(1,len(groups)))]:q['sampling_probability']=min(1,(512//len(groups))/len(qs));selected.append(q)
 (O/'native_replay_plan.json').write_text(json.dumps(selected,indent=2))
 rows=[]
 for tid in sorted(groups):
  qs=[r for r in selected if r['rule_key']==tid]
  rows+=frozen_predict(supp[tid],qs,'public','native')
  print('native replay',tid,len(qs),flush=True)
 return rows

def reference_eval():
 assert (O/'reference_formal_ledger.json').exists(), 'formal solver cohort must finish before scoring'
 plan=json.loads((O/'reference_plan.json').read_text());tables={t['table_id']:t for t in map(json.loads,(R/'runs/reference_dataset_v2/tables.jsonl').read_text().splitlines())}
 checks=[];formal=[];reuse=[]
 for q in plan['queries']:
  results=[]
  for level in ['coarse','fine','wide']:
   dest=O/'reference_results'/q['query_id']/level
   if not (dest/'receipt.json').exists():continue
   rec=json.loads((dest/'receipt.json').read_text());entry=dict(reference_id=q['query_id'],level=level,status=rec['status'])
   if rec['status']=='completed':entry['result']=json.loads((dest/'result.json').read_text())
   results.append(entry)
  check=diagnose(results)
  check=check[0] if check else dict(reference_id=q['query_id'],passed=False,complete=False)
  levels={r['level']:r['result'] for r in results if r['status']=='completed'}
  if check.get('complete'):
   v=components(levels['fine']['matrix_F_per_m'],q['spec']['metadata'])
   unc=np.max([abs(components(levels[k]['matrix_F_per_m'],q['spec']['metadata'])-v) for k in ['coarse','wide']],axis=0)
   # Component convergence threshold frozen in config; scale comes only from S.
   ys=np.sqrt(np.mean(np.array(tables[q['table_id']]['labels'])**2,axis=0))
   check['component_uncertainty']=unc.tolist();check['component_passed']=bool(np.all(unc<=.01*ys+1e-15));check['passed']=check['passed'] and check['component_passed']
   if q['split']=='formal' and check['passed']:formal.append(dict(q,reference=v.tolist(),reference_kind='direct_FEM_template_F_per_m',convergence_status='passed',reference_uncertainty=unc.tolist()))
  checks.append(check)
 (O/'reference_convergence.json').write_text(json.dumps(checks,indent=2))
 # Verify every reused support's geometry and direct-solve projection; no
 # passing label from a differently configured geometry can enter S.
 grid=json.loads((R/'runs/reference_design_v2/grid.json').read_text());manifest=json.loads((OLD/'manifest.json').read_text())
 assert sha(OLD/'fem_source_snapshot.py')==manifest['source_sha256']
 assert sha(R/'runs/reference_design_v2/grid.json')==manifest['grid_sha256']
 for tid in sorted(set(q['table_id'] for q in formal)):
  t=tables[tid];gs=[g for g in grid if g['reference_id']==tid]
  for i,g in enumerate(gs):
   for lev in ['coarse','fine','wide']:
    d=OLD/(g['id']+'-'+lev);spec=copy.deepcopy(g['spec']);spec['h']*=1 if lev=='coarse' else .5
    if lev=='wide':spec['extent']*=2;spec['materials'][-1][0]=spec['extent']
    assert json.loads((d/'spec.json').read_text())==spec
   result=json.loads((OLD/(g['id']+'-fine')/'result.json').read_text());v=components(result['matrix_F_per_m'],g['spec']['metadata']);assert np.array_equal(v,np.array(t['labels'][i]))
  reuse.append(dict(table_id=tid,n=len(gs),all_specs_exact=True,all_labels_bit_exact=True,source_sha256=manifest['source_sha256'],source_manifest_sha256=sha(OLD/'manifest.json')))
 (O/'support_reuse_checks.json').write_text(json.dumps(reuse,indent=2))
 rows=[]
 for tid in sorted(set(q['table_id'] for q in formal)):
  qs=[q for q in formal if q['table_id']==tid];rows+=frozen_predict(tables[tid],qs,'to_asap7','FEM')
  print('FEM',tid,len(qs),flush=True)
 return rows
if __name__=='__main__':
 torch.set_num_threads(1);kind=sys.argv[1];rows=public_replay() if kind=='native' else reference_eval()
 with (O/f'predictions_{kind}.jsonl').open('w') as f:
  for r in rows:f.write(json.dumps(r,allow_nan=False)+'\n')
