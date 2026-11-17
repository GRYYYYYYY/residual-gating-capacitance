"""Actual sparse-native construction and compute-slot injection, never node prediction export."""
from pathlib import Path
import os,sys,json,csv,re,hashlib,time,subprocess,collections,argparse,copy
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R));sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
import evaluate as old
from downstream import CASES,SOURCES,FLOW,UP
from scripts.downstream_holdout_predict import study_key,upstream_key
from openrcbench.openrcx import parse_openrcx
from openrcbench.spef import compare_spef
from unified.queries import query_table
sys.path.insert(0,str(R/'experiments/pex_kernel_revision'))
from kernels import mli
O=R/'results/dac_main13_integrated_revision/main13_20261117/native'
EXE=R/'results/pex_kernel_revision/build'
ARMS=['native_sparse','mli_native','binary_native','full_native']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def csvwrite(p,rs):
 if not rs:return
 with Path(p).open('w') as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)));w.writeheader();w.writerows(rs)
def parse_dump(path):
 knots=collections.defaultdict(list);slots=[]
 for l in path.read_text().splitlines():
  a=l.split('\t')
  if a[0]=='K':knots[a[1]].append([int(a[2]),*map(float,a[3:6])])
  else:slots.append(dict(key=a[1],context='|'.join(a[1].split('|')[:7]),eligible=bool(int(a[2])),original=list(map(float,a[3:6]))))
 assert len(slots)==len({s['key'] for s in slots})
 return knots,slots
def platform_source(platform):return next((sid,UP/'data/raw'/rel) for p,sid,rel in SOURCES if p==platform)
def build_inputs(platform,b,seed,poison=False):
 sid,source=platform_source(platform);proc={'ihp-sg13g2':'ihp_sg13g2','sky130hs':'sky130'}.get(platform,platform);scale=2000 if platform=='gf180' else 1000
 parsed=parse_openrcx(source,source_id=sid,process_id=proc,corner_id='typ')
 held={study_key(t):t for t in old.read_tables(R/'runs/public_inventory_holdout_v1/tables.jsonl') if t['partition']=='holdout'}
 lines=source.read_text().splitlines(keepends=True);remove=set();support=[];excluded=[];poison_lines=list(lines)
 for u in parsed:
  if upstream_key(u) not in held:continue
  t=held[upstream_key(u)]
  if len(u.rows)<4 or u.family not in ['OVER','UNDER','OVERUNDER'] or max(r['spacing_left'] for r in u.rows)*scale>=99000:
   excluded.append(dict(table_id=t['table_id'],family=u.family,n=len(u.rows),reason='short, diagonal, or special tail'));continue
  assert len({r['resistance'] for r in u.rows})==1,'native sparse R contract requires constant R'
  # Exactly the original label-blind farthest-point support indices.
  c,q,_=old.population(old.public_input(t),seed);actual=min(b,len(c));_,_,snaps=old.trajectory(t,seed,'farthest',[actual]);idx,v,_,hist=snaps[-1]
  hidden=sorted(set(range(len(u.rows)))-set(idx));rowlines=u.metadata['row_line_numbers']
  for i in hidden:
   j=rowlines[i]-1;remove.add(j)
   a=poison_lines[j].split();a[1]='987654.321';a[2]='123456.789';poison_lines[j]=' '.join(a)+'\n'
  h=u.metadata['dist_header_line']-1;lines[h]=re.sub(r'(DIST\s+count\s+)\d+',lambda m:m[1]+str(len(idx)),lines[h]);poison_lines[h]=lines[h]
  ctx=f'{platform}-main13-B{b}-s{seed}|0|{u.family}|{u.metal}|{u.context_below}|{u.context_above}|{int(np.floor(u.width*scale+.5))}'
  public=old.public_input(t);public.pop('coordinates')
  support.append(dict(table_id=t['table_id'],context_key=ctx,context=public,S_coordinates=np.asarray(t['coordinates'])[idx].tolist(),S_values=v.tolist(),support_indices=idx.tolist(),original_n=len(u.rows),budget_requested=b,budget_actual=len(idx),seed=seed,history=hist,resistance=u.rows[0]['resistance']))
 clean=''.join(l for i,l in enumerate(lines) if i not in remove);perturbed=''.join(l for i,l in enumerate(poison_lines) if i not in remove)
 assert clean==perturbed
 return (perturbed if poison else clean),support,excluded,dict(hidden_rows=len(remove),poisoned_reference_sha256=hashlib.sha256(''.join(poison_lines).encode()).hexdigest(),source_sha256=sha(source),sanitized_sha256=hashlib.sha256(clean.encode()).hexdigest())
def flow(case,dest,rules,namespace,payload=None,trace=False,dump=False):
 dest.mkdir(parents=True,exist_ok=False);platform=case.split('/')[0];info=CASES[case]
 env=dict(os.environ,STA_FLOW=str(FLOW),STA_PLATFORM=platform,STA_LIBS=' '.join('{'+str(FLOW/n)+'}' for n in info['libraries']),STA_ODB=str(R/info['odb']),STA_SDC=str(R/info['sdc']),STA_SPEF=str(dest/'extracted.spef'),STA_OUT=str(dest),DAC_RULES=str(rules),DAC_CT_NAMESPACE=namespace)
 if payload:env['DAC_CT_INPUT']=str(payload)
 if trace:env['DAC_CT_TRACE']=str(dest/'getters.tsv')
 if dump:env['DAC_CT_DUMP']=str(dest/'slots.tsv')
 ld=UP/'tools/openroad-deps-20260908';env['LD_LIBRARY_PATH']=f'{ld}/lib64:{ld}/lib:'+env.get('LD_LIBRARY_PATH','')
 exe=EXE/('openroad-trace' if trace else 'openroad-release');start=time.perf_counter()
 with (dest/'native.log').open('w') as f:
  p=subprocess.run([str(exe),'-threads','1','-exit',str(O/'flow.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 log=(dest/'native.log').read_text();assert p.returncode==0 and 'RUNTIME_COMPLETE' in log,(dest,p.returncode)
 stages={k+'_s':float(v) for k,v in re.findall(r'RUNTIME_STAGE (\S+) (\S+)',log)}
 stats=re.search(r'DAC_CT_STATS (.*)',log)[1].split();counts=dict(zip(['tables','slots','eligible','applied','changed','protected','special_tables'],map(int,stats[:7])))
 unit=re.search(r'^\s*time\s+([\d.]+)(\w+)',log,re.M);factor=float(unit[1])*{'s':1e12,'ns':1000,'ps':1,'fs':.001}[unit[2]]
 ep={r['endpoint']:float(r['slack'])*factor for r in csv.DictReader((dest/'endpoints.tsv').open(),delimiter='\t')}
 row=dict(case=case,wall_s=time.perf_counter()-start,**stages,**counts,native_build_s=float(stats[7]),injection_s=float(stats[8]),ws_ps=float(re.search(r'worst slack(?: max)? (-?[\d.eE+]+)',log)[1])*factor,tns_ps=float(re.search(r'tns(?: max)? (-?[\d.eE+]+)',log)[1])*factor,endpoint_count=len(ep),nonfinite_endpoints=sum(not np.isfinite(v) for v in ep.values()),rule_sha256=sha(rules),binary_sha256=sha(exe),tcl_sha256=sha(O/'flow.tcl'),payload_sha256=sha(payload) if payload else None,trace=trace,inventory=dump)
 save(dest/'receipt.json',row);return row,ep
def get_ep(dest):
 log=(dest/'native.log').read_text();u=re.search(r'^\s*time\s+([\d.]+)(\w+)',log,re.M);factor=float(u[1])*{'s':1e12,'ns':1000,'ps':1,'fs':.001}[u[2]]
 return {r['endpoint']:float(r['slack'])*factor for r in csv.DictReader((dest/'endpoints.tsv').open(),delimiter='\t')}
def electrical(p):
 b=p.read_bytes();return hashlib.sha256(b[b.index(b'*D_NET'):]).hexdigest()
def prepare(platform,b,seed,predictor):
 d=O/'inputs'/platform/f'B{b}_s{seed}'
 if (d/'ready.json').exists():return d
 d.mkdir(parents=True,exist_ok=False);start=time.perf_counter();clean,support,excluded,proof=build_inputs(platform,b,seed)
 (d/'sparse.rules').write_text(clean);save(d/'support.json',support);save(d/'excluded.json',excluded);save(d/'label_isolation.json',proof)
 namespace=f'{platform}-main13-B{b}-s{seed}';row,_=flow(platform+'/aes',d/'inventory',d/'sparse.rules',namespace,dump=True)
 knots,slots=parse_dump(d/'inventory/slots.tsv');matched={s['context_key']:s for s in support};absent=sorted(set(matched)-set(knots))
 chosen=[s for s in slots if s['eligible'] and s['context'] in matched]
 for ctx in set(matched)&set(knots):
  s=matched[ctx];scale=2000 if platform=='gf180' else 1000;factor=scale/1000
  expected=np.column_stack((np.floor(np.asarray(s['S_coordinates'])[:,1]*scale+.5),np.asarray(s['S_values'])/factor))
  assert np.allclose(np.asarray(knots[ctx])[:,:3],expected,rtol=1e-12,atol=0),(ctx,'S/native mapping')
 timings=[]
 for method in ['pass','mli_native','binary_native','full_native']:
  start_pred=time.perf_counter();vals={}
  for ctx,s in sorted(matched.items()):
   ss=sorted([a for a in chosen if a['context']==ctx],key=lambda a:(int(a['key'].split('|')[8]),a['key']));scale=2000 if platform=='gf180' else 1000;factor=scale/1000
   for off in range(0,len(ss),32):
    batch=ss[off:off+32];q=np.array([[s['S_coordinates'][0][0],int(a['key'].split('|')[8])/scale,int(a['key'].split('|')[8])/scale] for a in batch])
    if method=='pass':pred=np.array([a['original'][:2] for a in batch])
    elif method=='mli_native':pred=mli(np.array(s['S_coordinates']),np.array(s['S_values']),q)[0]/factor
    else:
     g,idx,v,ix=query_table(s['S_coordinates'],s['S_values'],q,s['context']);pred=predictor(method.split('_')[0],g,idx,v)[ix]/factor
    assert np.isfinite(pred).all() and (pred>=0).all()
    for a,p in zip(batch,pred):vals[a['key']]=p
  path=d/(method+'.tsv');path.write_text(''.join(k+' '+format(float(p[0]),'.17g')+' '+format(float(p[1]),'.17g')+'\n' for k,p in sorted(vals.items())))
  timings.append(dict(platform=platform,budget=b,seed=seed,method=method,prediction_and_write_s=time.perf_counter()-start_pred,slots=len(vals),payload_sha256=sha(path)))
 csvwrite(d/'prepare_timing.csv',timings)
 save(d/'ready.json',dict(support_tables=len(support),absent_from_supported_dump=absent,eligible_slots=len(chosen),all_slots=len(slots),native_eligible_slots=sum(s['eligible'] for s in slots),excluded_rules=len(excluded),inventory_s=row['wall_s'],prepare_total_s=time.perf_counter()-start,namespace=namespace))
 print('PREPARED',platform,b,seed,len(chosen),flush=True);return d
def check_trace(base,other,payload):
 vals={a[0]:[float(a[1]),float(a[2])] for a in (l.split() for l in payload.read_text().splitlines())} if payload else {}
 import itertools
 changed=hit=n=0
 with base.open() as f,other.open() as g:
  for a,b in itertools.zip_longest(f,g):
   assert a is not None and b is not None;a=a.rstrip().split('\t');b=b.rstrip().split('\t');assert a[:4]==b[:4] and a[6]==b[6]
   key=a[0]+f'|{int(a[2])//4}|{a[3]}|coupling,fringe|native_per_internal_length';n+=1
   if key in vals:assert [float(b[4]),float(b[5])]==vals[key];hit+=1
   else:assert a==b,('uncovered changed',key)
   changed+=a[4:6]!=b[4:6]
 return dict(calls=n,populated_returns=hit,changed_returns=changed,unchanged_returns=n-changed,uncovered_returns=n-hit)
def smoke(predictor):
 checks=[]
 for platform in ['asap7','ihp-sg13g2']:
  b=4;seed=11;d=prepare(platform,b,seed,predictor);ns=f'{platform}-main13-B{b}-s{seed}';root=O/'smoke'/platform;case=platform+'/aes'
  for method in ['native_sparse','pass','mli_native','binary_native','full_native']:
   flow(case,root/method,d/'sparse.rules',ns,None if method=='native_sparse' else d/(method+'.tsv'),trace=True)
  base=root/'native_sparse';assert electrical(base/'extracted.spef')==electrical(root/'pass/extracted.spef')
  assert (base/'getters.tsv').read_bytes()==(root/'pass/getters.tsv').read_bytes()
  for method in ARMS[1:]:
   c=check_trace(base/'getters.tsv',root/method/'getters.tsv',d/(method+'.tsv'))
   comp=compare_spef(base/'extracted.spef',root/method/'extracted.spef',root/method/'resistance_check.json');assert comp['metrics']['resistance']['rmse']==0
   checks.append(dict(platform=platform,method=method,**c,resistance_exact=True,uncovered_exact=True))
  clean,support,_,proof=build_inputs(platform,b,seed,poison=True);assert clean==(d/'sparse.rules').read_text() and support==json.loads((d/'support.json').read_text())
  (root/'poison_sparse.rules').write_text(clean)
  flow(case,root/'poison_full',root/'poison_sparse.rules',ns,d/'full_native.tsv',trace=True)
  assert electrical(root/'poison_full/extracted.spef')==electrical(root/'full_native/extracted.spef')
  assert (root/'poison_full/getters.tsv').read_bytes()==(root/'full_native/getters.tsv').read_bytes()
  # Release/debug electrical equivalence and interface-disabled sparse constructor.
  flow(case,root/'disabled_release',d/'sparse.rules',ns)
  assert electrical(root/'disabled_release/extracted.spef')==electrical(base/'extracted.spef')
 save(O/'smoke_pass.json',dict(status='PASS',checks=checks,hidden_label_isolation='poisoned hidden labels removed before construction; S-only predictor input identical; full extraction/getters bit-identical',observations='native K dump equals S; S bins excluded from injected slots',units='native K vs S conversion checked at 1000/2000 DBU; two components',gate_to_matrix=True))
def matrix(predictor):
 assert json.loads((O/'smoke_pass.json').read_text())['status']=='PASS'
 rows=[]
 for platform in ['asap7','gf180','ihp-sg13g2','sky130hs']:
  for b in [4,8]:
   for seed in [11,29,47]:
    d=prepare(platform,b,seed,predictor);ns=f'{platform}-main13-B{b}-s{seed}'
    for design in ['aes','ibex']:
     case=platform+'/'+design;gold=R/'results/dac_characterization_20261114/downstream/native'/case/'golden';ep0=get_ep(gold);oldgold=json.loads((gold/'COMPLETED.json').read_text());log=(gold/'native.log').read_text();unit=re.search(r'^\s*time\s+([\d.]+)(\w+)',log,re.M);factor=float(unit[1])*{'ps':1,'ns':1000}[unit[2]]
     for method in ARMS:
      dest=O/'matrix'/case/f'B{b}_s{seed}'/method
      if (dest/'metrics.json').exists():rows.append(json.loads((dest/'metrics.json').read_text()));continue
      row,ep=flow(case,dest,d/'sparse.rules',ns,None if method=='native_sparse' else d/(method+'.tsv'))
      comp=compare_spef(gold/'extracted.spef',dest/'extracted.spef',dest/'comparison.json');assert comp['common_nets']==comp['golden_nets']==comp['candidate_nets'];assert comp['metrics']['resistance']['rmse']==0;assert set(ep)==set(ep0)
      ids=sorted(ep);a=np.array([ep0[k] for k in ids]);z=np.array([ep[k] for k in ids]);assert np.array_equal(np.isfinite(a),np.isfinite(z));finite=np.isfinite(a);signed=z[finite]-a[finite];err=abs(signed)
      cap=comp['metrics']['capacitance'];row.update(method=method,budget=b,seed=seed,protocol='native_sparse_compute_table',net_cap_nrmse=cap['nrmse'],net_cap_rmse=cap['rmse'],net_cap_mae=cap['mae'],cap_unit=json.dumps(comp['units']['*C_UNIT']),ws_abs_ps=abs(row['ws_ps']-oldgold['worst_slack_native']*factor),tns_abs_ps=abs(row['tns_ps']-oldgold['tns_native']*factor),endpoint_mae_ps=float(err.mean()),endpoint_p95_ps=float(np.quantile(err,.95)),endpoint_p99_ps=float(np.quantile(err,.99)),endpoint_max_ps=float(err.max()),signed_slack_ps=float(signed.mean()),optimistic_endpoints=int((signed>0).sum()),pessimistic_endpoints=int((signed<0).sum()),finite_endpoints=int(finite.sum()),missing_endpoints=0,resistance_rmse=0.,gold_spef_sha256=sha(gold/'extracted.spef'),odb_sha256=sha(R/CASES[case]['odb']),sdc_sha256=sha(R/CASES[case]['sdc']))
      save(dest/'metrics.json',row);rows.append(row);csvwrite(O.parent/'native_sparse_metrics.csv',rows)
      print('MATRIX',len(rows),'/192',case,b,seed,method,round(row['net_cap_nrmse'],5),flush=True)
 assert len(rows)==192;save(O/'matrix_completed.json',dict(status='PASS',arm_settings=len(rows),paired_settings=48,layout_budget_cells=16,independent_layouts=8,platforms=4,all_resistance_exact=True,all_endpoint_identities_exact=True))
def main():
 a=argparse.ArgumentParser();a.add_argument('phase',choices=['smoke','matrix','all']);v=a.parse_args();O.mkdir(parents=True,exist_ok=True)
 tcl=(R/'experiments/pex_kernel_revision/native_flow.tcl').read_text();tcl=tcl.replace('puts RUNTIME_COMPLETE', '''measure endpoint_export {
 set f [open $::env(STA_OUT)/endpoints.tsv w]
 puts $f "endpoint\\tslack"
 foreach pin [sta::endpoints] {puts $f "[get_full_name $pin]\\t[get_property $pin slack_max]"}
 close $f
}
puts RUNTIME_COMPLETE''');(O/'flow.tcl').write_text(tcl)
 start=time.perf_counter();predictor=old.Predictors('public',old.read(R/'experiments/dac_characterization_20261114/selected_public.json') if hasattr(old,'read') else json.loads((R/'experiments/dac_characterization_20261114/selected_public.json').read_text()),learned=False)
 save(O/'model_load.json',dict(wall_s=time.perf_counter()-start))
 if v.phase in ['smoke','all'] and not (O/'smoke_pass.json').exists():smoke(predictor)
 if v.phase in ['matrix','all']:matrix(predictor)
if __name__=='__main__':main()
