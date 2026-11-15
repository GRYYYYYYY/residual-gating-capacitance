"""New computeTable preparation/injection. Never exports replacement rule nodes."""
from common import *
import subprocess,re,collections,argparse,importlib.util
import numpy as np
sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
saved=sys.modules.pop('common',None)
spec=importlib.util.spec_from_file_location('prior_predict',R/'experiments/dac_characterization_20261114/evaluate.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
from downstream import CASES,SOURCES,FLOW
from openrcbench.spef import compare_spef
from unified.queries import query_table
POLICY=dict(coverage='all eligible finite slots in source-held-out tables; original full characterization retained',chunk_limit=32,order='effective separation ascending per fixed context',source='immutable Full/Binary three-member ensemble',components=['coupling','fringe'],preserve='measurement-bin conflicts, boundary measure returns, resistance, special tables, unsupported contexts')

POLICY['coordinate_scale_per_um']={'asap7':1000.,'gf180':2000.,'ihp-sg13g2':1000.,'sky130hs':1000.}
POLICY['full_checkpoints']=[c['sha256'] for c in read(R/'configs/paper_models.json')['public']['checkpoints']]
_control=Path(read(R/'experiments/dac_characterization_20261114/paths.json')['control_root'])
POLICY['binary_checkpoints']=[read(_control/'runs'/f'public_binary_s{i}'/'COMPLETED.json')['checkpoint_sha256'] for i in range(3)]

def source(platform):return next(UP/'data/raw'/rel for p,s,rel in SOURCES if p==platform)
def namespace(platform):return platform+'-typ-'+digest([sha(source(platform)),POLICY])[:24]
def run_one(case,method,block=0,trace=False,dump=False):
 platform,design=case.split('/');info=CASES[case];dest=O/('inventory' if dump else 'validation' if trace else 'native')/platform/design/method/str(block);dest.mkdir(parents=True,exist_ok=True)
 exe=(UP/'tools/openroad-install-20260909/bin/openroad') if method=='original' else O/'build'/('openroad-trace' if trace else 'openroad-release')
 env=dict(os.environ,STA_FLOW=str(FLOW),STA_PLATFORM=platform,STA_LIBS=' '.join('{'+str(FLOW/n)+'}' for n in info['libraries']),STA_ODB=str(R/info['odb']),STA_SDC=str(R/info['sdc']),STA_SPEF=str(dest/'extracted.spef'),DAC_RULES=str(source(platform)),DAC_CT_NAMESPACE=namespace(platform))
 if dump:env['DAC_CT_DUMP']=str(dest/'slots.tsv')
 if trace:env['DAC_CT_TRACE']=str(dest/'getters.tsv')
 if method in ['pass','full','binary']:env['DAC_CT_INPUT']=str(O/'payloads'/f'{platform}_{method}.tsv')
 ld=UP/'tools/openroad-deps-20260908';env['LD_LIBRARY_PATH']=f'{ld}/lib64:{ld}/lib:'+env.get('LD_LIBRARY_PATH','')
 before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
 with (dest/'native.log').open('w') as f:
  p=subprocess.run(['/usr/bin/time','-v','-o',str(dest/'resource.txt'),str(exe),'-threads','1','-exit',str(H/'native_flow.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 after=resource.getrusage(resource.RUSAGE_CHILDREN);wall=time.perf_counter()-start;log=(dest/'native.log').read_text();assert p.returncode==0 and 'RUNTIME_COMPLETE' in log,(case,method,p.returncode)
 dbu=int(re.search(r'DAC_CT_DBU (\d+)',log)[1]);assert max(1000.,dbu)==POLICY['coordinate_scale_per_um'][platform]
 stages={n+'_s':float(v) for n,v in re.findall(r'RUNTIME_STAGE (\S+) (\S+)',log)}
 stats=re.search(r'DAC_CT_STATS (.*)',log);counts={}
 if stats:
  a=stats[1].split();counts=dict(zip(['tables','slots','eligible','applied','changed','protected','special_tables'],map(int,a[:7])));counts.update(native_build_s=float(a[7]),injection_s=float(a[8]))
 b=(dest/'extracted.spef').read_bytes();electrical=hashlib.sha256(b[b.index(b'*D_NET'):]).hexdigest()
 gold=R/'results/dac_characterization_20261114/downstream/native'/platform/design/'golden/extracted.spef';gb=gold.read_bytes();nativehash=hashlib.sha256(gb[gb.index(b'*D_NET'):]).hexdigest()
 if method in ['original','disabled','pass']:assert electrical==nativehash,(case,method,'pass-through electrical mismatch')
 comp=compare_spef(gold,dest/'extracted.spef',dest/'comparison.json')
 assert comp['metrics']['resistance']['nrmse']==0.,(case,method,'resistance changed')
 unit=re.search(r'^\s*time\s+([\d.]+)(\w+)',log,re.M);factor=float(unit[1])*{'s':1e12,'ns':1e3,'ps':1.,'fs':1e-3}[unit[2]]
 slack=float(re.search(r'worst slack(?: max)? (-?[\d.eE+]+)',log)[1]);tns=float(re.search(r'tns(?: max)? (-?[\d.eE+]+)',log)[1])
 row=dict(case=case,method=method,block=block,wall_s=wall,cpu_s=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,**stages,**counts,electrical_sha256=electrical,identical_native=electrical==nativehash,trace=trace,inventory_dump=dump,worst_slack_ps=slack*factor,tns_ps=tns*factor,rule_sha256=sha(source(platform)),binary_sha256=sha(exe),namespace=namespace(platform),dbu_per_um=dbu,peak_rss_kib=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',(dest/'resource.txt').read_text())[1]))
 write(dest/'receipt.json',dict(**row,comparison=comp));print(case,method,block,'wall',round(wall,3),'slots',counts.get('applied'),flush=True);return row

def inventory():
 pin();rows=[]
 for case in sorted(CASES):rows.append(run_one(case,'disabled',dump=True))
 csvwrite(O/'inventory_cost.csv',rows)
 write(O/'injection_contract.json',dict(policy=POLICY,insert='extDistRCTable::readRules immediately after interpolate(4,-1,rcPool), before any getter',key='process/corner/rule+policy hash | model corner | family | metal | lower | upper | mapped integer width | slot | represented separation | coupling,fringe | native_per_internal_length',baseline_rules='unchanged full original rule files',resistance='setCoupling/setFringe only; all other fields and pointer return path preserved',special='whole sentinel tables and diagonal/resistance read paths excluded',cost='inventory enumerates all loaded rules, no layout access filtering; public API requires one inventory extraction, counted in cold preparation',online_inference=False))

def parse_dump(path):
 knots=collections.defaultdict(list);slots=[]
 for l in Path(path).read_text().splitlines():
  a=l.split('\t')
  if a[0]=='K':knots[a[1]].append([int(a[2]),*map(float,a[3:6])])
  else:slots.append(dict(key=a[1],context='|'.join(a[1].split('|')[:7]),eligible=bool(int(a[2])),original=list(map(float,a[3:6]))))
 return knots,slots

def prepare():
 pin();start=stamp();ts=[json.loads(l) for l in (R/'runs/public_inventory_holdout_v1/tables.jsonl').read_text().splitlines()];data_load=elapsed(start);loadstart=stamp();P=old.Predictors('public',read(R/'experiments/dac_characterization_20261114/selected_public.json'),learned=False);model_load=elapsed(loadstart)
 dest=O/'payloads';dest.mkdir(exist_ok=True);records=[];rows=[]
 for platform in sorted({c.split('/')[0] for c in CASES}):
  matching_start=stamp();k,slots=parse_dump(O/'inventory'/platform/'aes/disabled/0/slots.tsv');ki,si=parse_dump(O/'inventory'/platform/'ibex/disabled/0/slots.tsv')
  assert k==ki and slots==si,(platform,'rule grid depends on design')
  proc={'ihp-sg13g2':'ihp_sg13g2','sky130hs':'sky130'}.get(platform,platform);scale=2000. if platform=='gf180' else 1000.;factor=scale/1000.
  matched={};unmatched=[]
  for ctx,ks in k.items():
   a=ctx.split('|');fam=a[2];met,below,above,width=map(int,a[3:7]);kn=np.array(ks);candidates=[]
   for t in ts:
    if t['process_id']!=proc or t['family']!=fam or t['metal']!=met or len(t['coordinates'])!=len(ks):continue
    x=np.array(t['coordinates']);y=np.array(t['labels'])
    if round(x[0,0]*scale)!=width:continue
    if np.array_equal(np.floor(x[:,1]*scale+.5).astype(int),kn[:,0]) and np.allclose(y/factor,kn[:,1:3],rtol=1e-10,atol=1e-18):candidates.append(t)
   if len(candidates)==1 and candidates[0]['partition']=='holdout' and len(ks)>=4:matched[ctx]=candidates[0]
   else:unmatched.append(dict(context=ctx,candidates=len(candidates),reason='non-heldout, ambiguous, or fewer than four real supports'))
  chosen=[s for s in slots if s['eligible'] and s['context'] in matched]
  assert chosen,(platform,'no eligible held-out slots')
  support_mapping=elapsed(matching_start)
  for method in ['pass','binary','full']:
   begin=stamp();vals={}
   for ctx,t in sorted(matched.items()):
    ss=sorted([s for s in chosen if s['context']==ctx],key=lambda s:(int(s['key'].split('|')[8]),s['key']))
    for off in range(0,len(ss),32):
     batch=ss[off:off+32]
     if method=='pass':pred=np.array([s['original'][:2] for s in batch])
     else:
      q=np.array([[t['coordinates'][0][0],int(s['key'].split('|')[8])/scale,int(s['key'].split('|')[8])/scale] for s in batch]);g,o,v,ix=query_table(t['coordinates'],t['labels'],q,{k:v for k,v in old.public_input(t).items() if k!='coordinates'});pred=P(method,g,o,v)[ix]/factor
     for s,p in zip(batch,pred):vals[s['key']]=p
   predcost=elapsed(begin);begin=stamp();path=dest/f'{platform}_{method}.tsv'
   with path.open('w') as f:
    for key,p in sorted(vals.items()):f.write(key+' '+format(float(p[0]),'.17g')+' '+format(float(p[1]),'.17g')+'\n')
   rows.append(dict(platform=platform,method=method,slots=len(vals),tables=len(matched),prediction_wall_s=predcost['wall_s'],prediction_cpu_s=predcost['cpu_s'],write_wall_s=elapsed(begin)['wall_s'],payload_bytes=path.stat().st_size,payload_sha256=sha(path),canonical_Q_hash=digest(sorted(vals)),design_independent_grid_verified=True))
   print(platform,method,len(vals),'slots',round(predcost['wall_s'],3),'s',flush=True)
  records.append(dict(platform=platform,support_mapping=support_mapping,total_dump_slots=len(slots),eligible_slots=sum(s['eligible'] for s in slots),injected_slots=len(chosen),matched_tables={k:v['table_id'] for k,v in matched.items()},excluded_contexts=unmatched,scale=scale,all_real_supports=True,namespace=namespace(platform)))
 csvwrite(O/'prepare_timing.csv',rows);write(O/'preparation.json',dict(**elapsed(start),model_bundle_load=model_load,data_load=data_load,platforms=records,rows=rows,policy=POLICY))

def validate():
 pin();rs=[];checks=[]
 for case in sorted(CASES):
  # Native disabled/pass traces validate getters, values, R and order.
  for method in ['disabled','pass','binary','full']:rs.append(run_one(case,method,trace=True))
  base=O/'validation'/case;orig=(base/'disabled/0/getters.tsv').read_bytes();pas=(base/'pass/0/getters.tsv').read_bytes();assert orig==pas,(case,'getter pass-through mismatch')
  platform=case.split('/')[0];payload={}
  for method in ['binary','full']:
   payload={a[0]:[float(a[1]),float(a[2])] for a in (l.split() for l in (O/'payloads'/f'{platform}_{method}.tsv').read_text().splitlines())};n=changed=hit=0
   with (base/'disabled/0/getters.tsv').open() as f,(base/method/'0/getters.tsv').open() as g:
    import itertools
    for a,b in itertools.zip_longest(f,g):
     assert a is not None and b is not None;a=a.rstrip().split('\t');b=b.rstrip().split('\t');assert a[:4]==b[:4] and a[6]==b[6]
     n+=1;ctx=a[0];slot=int(a[2])//4;sep=int(a[3]);key=ctx+f'|{slot}|{sep}|coupling,fringe|native_per_internal_length'
     if key in payload:
      assert [float(b[4]),float(b[5])]==payload[key];hit+=1
     else:assert a==b,(case,method,key,'uncovered return changed')
     changed+=a[4:6]!=b[4:6]
   checks.append(dict(case=case,method=method,getter_calls=n,injected_getter_calls=hit,changed_getter_calls=changed,pass_through_bit_exact=True,resistance_exact=True,uncovered_returns_exact=True))
 csvwrite(O/'validation_timing.csv',rs);write(O/'pass_through.json',dict(passed=True,checks=checks))

def benchmark():
 # Inventory and getter validation must never share output paths.
 if not (O/'inventory').exists():
  prior=O/'inventory_cost.csv'
  if prior.exists():prior.rename(O/'inventory_cost_before_path_separation.csv')
  inventory()
  matched=[]
  for case in sorted(CASES):
   a=O/'validation'/case/'disabled/0/slots.tsv';b=O/'inventory'/case/'disabled/0/slots.tsv'
   assert a.read_bytes()==b.read_bytes(),case
   matched.append(dict(case=case,sha256=sha(b),exact_grid_equal=True))
  write(O/'inventory_path_separation.json',dict(checks=matched,reason='separate raw inventory and getter-validation receipts; old inventory timing CSV retained, overwritten diagnostic logs not reconstructed'))
 pin();rs=[];tasks=[(c,m) for c in sorted(CASES) for m in ['original','disabled','pass','binary','full']];rng=np.random.default_rng(20261115)
 for rep in range(3):
  for i in rng.permutation(len(tasks)):
   c,m=tasks[i];rs.append(run_one(c,m,rep));csvwrite(O/'native_flow_timing.csv',rs)
 write(O/'native_completed.json',dict(runs=len(rs),cpu_s=sum(r['cpu_s'] for r in rs),wall_s=sum(r['wall_s'] for r in rs),trace=False,protocol='same unchanged original rules, 8 layouts x 5 modes x3; new path separately timed'))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('phase',choices=['inventory','prepare','validate','benchmark']);v=a.parse_args();globals()[v.phase]()
