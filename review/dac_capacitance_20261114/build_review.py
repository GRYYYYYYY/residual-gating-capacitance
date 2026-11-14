"""Read-only evidence reconstruction. No model loading, inference, training or solver calls.
Writes only within this review directory; immutable source results are never rewritten.
"""
import csv,gzip,json,hashlib,subprocess,sys,collections,datetime,shutil,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'experiments/dac_characterization_20261114'))
from common import ROOT,HERE,PATHS,MODELS,tables,source_config,sha
from pdkcap.metrics import summarize
from pdkcap.common import read_tables,FAMILIES
from pdkcap.train import unique_tables
R=ROOT/'results/dac_characterization_20261114';BASE='269a86b15a5619400447266c186485a641b8a8ef'
assert subprocess.check_output(['git','rev-parse','269a86b'],cwd=ROOT,text=True).strip()==BASE
refs={}
def ref(p,role='input'):
 p=Path(p).absolute();key=str(p)
 if key not in refs:refs[key]=dict(path=key,sha256=sha(p),bytes=p.stat().st_size,role=role)
 return refs[key]['sha256']
def read(p):ref(p);return json.loads(Path(p).read_text())
def rows(p):ref(p);return [json.loads(l) for l in gzip.open(p,'rt')]
def csvread(p):ref(p);return list(csv.DictReader(Path(p).open()))
def save(name,rs):
 assert rs,name
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)),lineterminator='\n');w.writeheader();w.writerows(rs)
def js(name,d):(OUT/name).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def err(r):
 sy=np.asarray(r['squared_truth']);se=np.asarray(r['squared_error']);live=sy>0
 return float(np.sqrt(se[live]/sy[live]).mean()) if live.any() else None
def mean(rs,key):
 v=[r.get(key) for r in rs];return float(np.mean(v)) if all(x is not None for x in v) else None
main=[];thresholds={};freezes=[];checks=[]
for s in MODELS:
 p=R/f'confirmation_{s}';done=read(p/'COMPLETED.json');frozen=read(p/'FROZEN.json');rs=rows(p/'records.jsonl.gz')
 assert len(rs)==done['records'] and done['failed']==0 and sha(p/'records.jsonl.gz')==done['records_sha256'];main+=rs
 sel=read(HERE/f'selected_{s}.json');thresholds[s]=sel['thresholds']
 old=json.loads(subprocess.check_output(['git','show',f'1486537:experiments/dac_characterization_20261114/selected_{s}.json'],cwd=ROOT,text=True));assert old==sel==frozen['selection']
 val=rows(R/f'validation_{s}/records.jsonl.gz');vv=collections.defaultdict(list)
 for r in val:
  if r['method']=='anchor':vv[r['table_id']].append(r)
 chosen=[max([r for r in rr if r['budget']<=8],key=lambda r:r['budget']) for rr in vv.values()]
 vals=[err(r) for r in chosen if err(r) is not None];np.testing.assert_array_equal(np.quantile(vals,[.25,.5,.75]),sel['thresholds'])
 freezes.append(dict(setting=s,thresholds=sel['thresholds'],validation_tables_total=len(tables(s,'val')),validation_eligible=len(chosen),validation_defined=len(vals),validation_data_seed=11,validation_budget=8,validation_records_sha256=sha(R/f'validation_{s}/records.jsonl.gz'),selection_sha256=sha(HERE/f'selected_{s}.json'),selection_local_mtime_utc=datetime.datetime.fromtimestamp((HERE/f'selected_{s}.json').stat().st_mtime,datetime.timezone.utc).isoformat(),freeze_commit='14865375475a067364fe6f96483af3712882e752',freeze_commit_time='2026-11-13T22:52:03+00:00',confirmation_frozen_mtime_utc=datetime.datetime.fromtimestamp((p/'FROZEN.json').stat().st_mtime,datetime.timezone.utc).isoformat(),application_basis='none; source-validation anchor-error quartiles, not STA-certified tolerance'))
primary=[r for r in main if r['strategy']=='farthest'];lookup={(r['setting'],r['table_id'],r['data_seed'],r['budget']):r for r in primary if r['method']=='full'}
for s in ('reference','to_asap7'):
 rr=rows(R/f'attention/{s}_confirmation/records.jsonl.gz');assert read(R/f'attention/{s}_confirmation/COMPLETED.json')['failed']==0
 for r in rr:
  base=lookup[r['setting'],r['table_id'],r['data_seed'],r['budget']]
  assert r['support_indices']==base['support_indices'] and r['query_indices']==base['query_indices']
  # Validated CPU can be derived from identical purchased geometries. No new measurement.
  r['solver_cpu_seconds_validated']=0. if r['method'].endswith('_zero') else base['solver_cpu_seconds_validated']
 primary+=rr
methods=['anchor','cmi','gp','affine','residual','binary','full','pruned','mlp_adapt','cnp','attentioncap_adapted','pchip','mlp_zero','attentioncap_zero']
ZERO={'mlp_zero','attentioncap_zero'};ADAPT={'mlp_adapt','attentioncap_adapted'}
selected={s:read(R/f'learning/{s}_selection.json') for s in MODELS}
att_sel={s:read(R/f'attention/{s}_selection.json') for s in ('reference','to_asap7')}
by=collections.defaultdict(list)
for r in primary:assert r['status']=='ok';by[r['setting'],r['method'],r['budget']].append(r)
same=[];status=[]
for s in MODELS:
 for m in methods:
  budgets=sorted(b for ss,mm,b in by if ss==s and mm==m)
  status.append(dict(setting=s,method=m,status='completed' if budgets else 'not_run',budgets=json.dumps(budgets),reason=('public geometry/material matrix representation not defined; no public AttentionCap execution' if not budgets else 'rank2 linear fallback, not PCHIP' if m=='pchip' and s!='public' else 'ablation only; validation rejected pruning' if m=='pruned' else 'source-only Q control; B observations restored in returned table' if m in ZERO else ''),infeasible_budgets='16,32,64 (zero eligible public tables)' if s=='public' else '',native_status='completed B4/B8 on eligible public holdouts' if s=='public' and m in ['cmi','anchor','affine','binary','full'] else 'not_run'))
  for b in budgets:
   rr=by[s,m,b];nexpected=(338 if s=='public' else 16 if s=='reference' else 8)*3;assert len(rr)==nexpected
   for r in rr:
    base=lookup[s,r['table_id'],r['data_seed'],b];assert r['support_indices']==base['support_indices'] and r['query_indices']==base['query_indices']
   measure=summarize(rr);steps=selected[s]['mlp']['adapt_steps'] if m=='mlp_adapt' else att_sel[s]['adapt_steps'] if m=='attentioncap_adapted' else 0
   same.append(dict(setting=s,method=m,budget=b,records=len(rr),tables=len({r['table_id'] for r in rr}),target_labels_for_Q=0 if m in ZERO else b,restored_observation_count=b,components_per_query=len(rr[0]['squared_truth']),query_rows_min=min(r['n'] for r in rr),query_rows_max=max(r['n'] for r in rr),macro_nrmse=measure['nrmse'],macro_native_mae=float(np.mean([c['mae'] for c in measure['cells']+measure['zero_truth_groups']])),native_unit=rr[0]['unit'],target_fit_steps_per_member=steps,ensemble_members=3 if m in ['full','pruned','residual','binary','mlp_adapt','mlp_zero','cnp','attentioncap_adapted','attentioncap_zero'] else 0,adaptation_only_wall_seconds=None if m in ADAPT else 0.,completion_without_adaptation_wall_seconds=None if m in ADAPT else mean(rr,'prediction_and_adaptation_wall_seconds'),combined_completion_adaptation_wall_seconds=mean(rr,'prediction_and_adaptation_wall_seconds'),timing_scope='call includes features/support/ensemble; excludes initial population/model load; adaptation split unavailable' if m in ADAPT else 'call total; initial population/model load excluded',fine_cpu_seconds_mean=0. if m in ZERO else mean(rr,'solver_cpu_seconds_fine'),validated_cpu_seconds_mean=0. if m in ZERO else mean(rr,'solver_cpu_seconds_validated'),cost_kind='Q source-only; restoring B observations not free' if m in ZERO else 'simulated rule access; solver cost unknown' if s=='public' else 'recorded-cost replay; fine / coarse+fine+wide',execution_success_fraction=1.,missing_records=0,failed_records=0))
save('same_budget.csv',same);save('method_status.csv',status)
# All methods are judged on identical table/seed trajectories within each setting.
tr=collections.defaultdict(list)
for r in primary:
 if r['method'] not in ZERO:tr[r['setting'],r['method'],r['table_id'],r['data_seed']].append(r)
trajectories=[]
for (s,m,tid,seed),rr in sorted(tr.items()):
 rr=sorted(rr,key=lambda r:r['budget']);first=rr[0];last=rr[-1];zero=all(err(r) is None for r in rr)
 for qi,tau in enumerate(thresholds[s]):
  hit=[r for r in rr if err(r) is not None and err(r)<=tau];best=hit[0] if hit else None
  trajectories.append(dict(setting=s,method=m,table_id=tid,data_seed=seed,threshold_index=qi,threshold=tau,status='undefined_zero_truth' if zero else 'reached' if best else 'not_reached',first_measured_budget=first['budget'],first_measured_nrmse=err(first),first_measured_reached=best is not None and best['budget']==first['budget'],first_measured_attainment_budget=best['budget'] if best else None,queries_at_attainment=best['budget'] if best else None,fine_cpu_at_attainment=best.get('solver_cpu_seconds_fine') if best else None,validated_cpu_at_attainment=best.get('solver_cpu_seconds_validated') if best else None,combined_wall_at_attainment=best['prediction_and_adaptation_wall_seconds'] if best else None,max_measured_budget=last['budget'],queries_at_max=last['budget'],fine_cpu_at_max=last.get('solver_cpu_seconds_fine'),validated_cpu_at_max=last.get('solver_cpu_seconds_validated'),initial_support_queries=4,missing_records=0,execution_failures=0))
save('threshold_trajectories.csv',trajectories)
coverage=[]
groups=collections.defaultdict(list)
for r in trajectories:groups[r['setting'],r['method'],r['threshold_index']].append(r)
for (s,m,qi),rr in groups.items():
 live=[r for r in rr if r['status']!='undefined_zero_truth'];hit=[r for r in live if r['status']=='reached'];bad=[r for r in live if r['status']=='not_reached']
 def total(key,items):return sum(r[key] for r in items) if items and all(r[key] is not None for r in items) else None
 charged=[dict(r,policy_queries=r['queries_at_attainment'] if r['status']=='reached' else r['queries_at_max'],policy_fine=r['fine_cpu_at_attainment'] if r['status']=='reached' else r['fine_cpu_at_max']) for r in rr]
 coverage.append(dict(setting=s,method=m,threshold_index=qi,threshold=rr[0]['threshold'],scheduled=len(rr),defined=len(live),zero_truth=len(rr)-len(live),reached=len(hit),not_reached=len(bad),missing=0,execution_failed=0,coverage_defined=len(hit)/len(live),coverage_all_scheduled_lower_bound=len(hit)/len(rr),at_first_measured_budget=sum(r['first_measured_reached'] for r in hit),sum_queries_reached=total('queries_at_attainment',hit),sum_fine_cpu_reached=total('fine_cpu_at_attainment',hit),sum_validated_cpu_reached=total('validated_cpu_at_attainment',hit),sum_queries_first_hit_else_max_all=total('policy_queries',charged),sum_fine_cpu_first_hit_else_max_all=total('policy_fine',charged),sum_queries_max_all=total('queries_at_max',rr),sum_fine_cpu_max_all=total('fine_cpu_at_max',rr),cost_scope='reached-only is conditional; first-hit-else-max is retrospective cost policy including censored/undefined; no online stopping policy executed'))
save('coverage_cost.csv',coverage)
# Original paired claims must reconcile exactly against derived rows.
for s,n,q,cpu in [('reference',48,192,1367.8916334690002),('to_asap7',24,96,765.4129828920001)]:
 for m in ('full','binary','mlp_adapt'):
  r=next(r for r in coverage if (r['setting'],r['method'],r['threshold_index'])==(s,m,1));assert r['scheduled']==r['reached']==r['at_first_measured_budget']==n and r['sum_queries_reached']==q;assert abs(r['sum_fine_cpu_reached']-cpu)<1e-8
# Per-seed and seed-mean downstream differences, including zero denominators and tails.
native=csvread(R/'summary/downstream_raw.csv');assert len(native)==240
metrics=['net_cap_nrmse','net_cap_mae_native','slack_mae_ns','slack_p95_ns','slack_p99_ns','slack_max_abs_ns','ws_abs_ns','tns_abs_ns','false_negative','false_positive','spearman']+[f'{a}_overlap_at{k}' for a in ('endpoint','full_path') for k in (10,20,50,100)]
nd=[];allcells={}
for r in native:allcells[r['case'],int(r['budget']),r['data_seed'],r['method']]=r
for case in sorted({r['case'] for r in native}):
 for b in (4,8):
  for seed in ('11','29','47','mean'):
   for comp in ('cmi','anchor','affine','binary'):
    for metric in metrics:
     def val(m):return float(np.mean([float(allcells[case,b,z,m][metric]) for z in ('11','29','47')])) if seed=='mean' else float(allcells[case,b,seed,m][metric])
     a,c=val('full'),val(comp);d=a-c;tol=max(1e-12,1e-9*max(abs(a),abs(c)));higher='overlap' in metric or metric=='spearman';tie=abs(d)<=tol
     nd.append(dict(case=case,budget=b,data_seed=seed,comparator=comp,metric=metric,higher_is_better=higher,full=a,comparator_value=c,full_minus_comparator=d,absolute_difference=abs(d),relative_difference_percent=100*d/abs(c) if c!=0 else None,zero_denominator=c==0,tie_tolerance=tol,outcome='tie' if tie else 'full_better' if (d>0 if higher else d<0) else 'full_worse'))
save('downstream_deltas.csv',nd)
ds=[]
for comp in ('cmi','anchor','affine','binary'):
 for metric in metrics:
  rr=[r for r in nd if r['comparator']==comp and r['metric']==metric and r['data_seed']=='mean'];bad=[r for r in rr if r['outcome']=='full_worse'];worst=max(bad,key=lambda r:abs(r['full_minus_comparator'])) if bad else None
  ds.append(dict(comparator=comp,metric=metric,cells=len(rr),full_better=sum(r['outcome']=='full_better' for r in rr),ties=sum(r['outcome']=='tie' for r in rr),full_worse=len(bad),mean_signed_difference=float(np.mean([r['full_minus_comparator'] for r in rr])),min_signed_difference=min(r['full_minus_comparator'] for r in rr),max_signed_difference=max(r['full_minus_comparator'] for r in rr),relative_percent_min=min((r['relative_difference_percent'] for r in rr if r['relative_difference_percent'] is not None),default=None),relative_percent_max=max((r['relative_difference_percent'] for r in rr if r['relative_difference_percent'] is not None),default=None),worst_degradation_case=worst['case'] if worst else None,worst_degradation_budget=worst['budget'] if worst else None,worst_degradation_signed_difference=worst['full_minus_comparator'] if worst else None))
save('downstream_delta_summary.csv',ds)
# Map all original holdouts, including the one excluded table.
sys.path.insert(0,str(ROOT/'scripts'))
from downstream_holdout_predict import study_key,upstream_key
from openrcbench.io import read_jsonl
held=[t for t in read_tables(ROOT/'runs/public_inventory_holdout_v1/tables.jsonl') if t['partition']=='holdout'];assert len(held)==84
upath=Path(PATHS['upstream_root'])/'data/processed/dataset.jsonl';ref(upath);up={upstream_key(t):t for t in read_jsonl(upath)}
export=read(R/'downstream/rules/manifest.json');supp=collections.defaultdict(list)
for r in export['support']:supp[r['table_id']].append(r)
mapping=[]
for t in held:
 u=up[study_key(t)];n=len(t['coordinates']);included=n>=4;ss=supp[t['table_id']]
 assert bool(ss)==included
 if included:assert len(ss)==6 and all(r['upstream_id']==u.table_id for r in ss)
 for i,row in enumerate(u.rows):
  for j,target in enumerate(t['target_names']):assert float(row[target])==float(t['labels'][i][j])
 mapping.append(dict(table_id=t['table_id'],upstream_id=u.table_id,source_id=t['source_id'],process_id=t['process_id'],family=t['family'],metal=t['metal'],nodes=n,included=included,reason='eligible; common S/Q for all five native methods' if included else 'n<4; cannot meet registered common support/query rule; left golden for all methods',applies_to='cmi,anchor,affine,binary,full',episodes=len(ss),actual_B4=sorted({r['budget_actual'] for r in ss if r['budget_requested']==4}),actual_B8=sorted({r['budget_actual'] for r in ss if r['budget_requested']==8}),coordinates_sha256=hashlib.sha256(json.dumps(t['coordinates'],sort_keys=True).encode()).hexdigest()))
assert sum(r['included'] for r in mapping)==83;save('downstream_table_map.csv',mapping)
# Reverse-direction results are separate, not full-gate transfer.
reverse=rows(R/'reverse_transfer/records.jsonl.gz');revsummary=[]
for m in ('mlp_zero','mlp_adapt'):
 for b in (4,8,16,32,64):
  rr=[r for r in reverse if r['method']==m and r['budget']==b];assert len(rr)==24 and all(r['status']=='ok' for r in rr)
  charged=[]
  for r in rr:
   match=lookup['reference',r['table_id'],r['data_seed'],b]
   assert r['support_indices']==match['support_indices'] and r['query_indices']==match['query_indices']
   charged.append(match)
  revsummary.append(dict(setting='asap7_to_freepdk15',method=m,budget=b,records=len(rr),macro_nrmse=summarize(rr)['nrmse'],target_labels=0 if m=='mlp_zero' else b,target_fit_steps=0 if m=='mlp_zero' else 200,combined_completion_adaptation_wall_seconds=mean(rr,'prediction_and_adaptation_wall_seconds'),separate_adaptation_wall_seconds=None if m=='mlp_adapt' else 0.,fine_cpu_seconds_mean=0. if m=='mlp_zero' else mean(charged,'solver_cpu_seconds_fine'),validated_cpu_seconds_mean=0. if m=='mlp_zero' else mean(charged,'solver_cpu_seconds_validated'),cost_provenance='derived recorded cost from exactly matched reference support/query; not new timing',execution_failed=0))
save('reverse_transfer.csv',revsummary)
# Training evidence: enumerate checkpoints and reconstruct support counts from sampler,
# without calling encoders or training. Counts are replay-derived, not historical logs.
checkpoint_rows=[];support_hist=[];datasets=[];seen_data={};warm=set()
def data_pool(s,cfg):
 p=ROOT/cfg['data'];frozen_path=p;expected=None
 if s!='public' and (Path(PATHS['solver_root'])/cfg['data']).exists():p=Path(PATHS['solver_root'])/cfg['data']
 # Absolute control paths can point into a different read-only worktree; reuse full source pool.
 if not p.exists():p=ROOT/source_config(s)['data']
 return p,unique_tables([t for t in read_tables(p) if t['partition']=='train' and len(t['coordinates'])>=2])
def replay(ts,seed,steps,width=True):
 rng=np.random.default_rng(seed);hist=collections.Counter();groups={f:[t for t in ts if t['family']==f] for f in FAMILIES}
 cached={}
 for f,pool in groups.items():
  procs=sorted({t['process_id'] for t in pool});cached[f]=(procs,[[t for t in pool if t['process_id']==p] for p in procs])
 widths={t['table_id']:np.unique(np.asarray(t['coordinates'])[:,0],return_counts=True)[1] for t in ts}
 for step in range(steps):
  for family in FAMILIES:
   procs,pools=cached[family];pool=pools[int(rng.integers(len(procs)))];t=pool[int(rng.integers(len(pool)))];protocols=['mcar','block','extrapolation']+(['width'] if width and t['width_count']>1 else [])
   protocol=protocols[int(rng.integers(len(protocols)))];ratio=(.1,.3,.5,.7)[int(rng.integers(4))];seedmask=int(rng.integers(2**31));n=len(t['coordinates']);observed=n-int(widths[t['table_id']][seedmask%len(widths[t['table_id']])]) if protocol=='width' else n-min(n-1,max(1,round(n*ratio)))
   hist[protocol,ratio,n,observed]+=1
 return hist
for s in MODELS:
 for seed,c in enumerate(MODELS[s]['checkpoints']):
  p=ROOT/c['path'];assert ref(p,'checkpoint')==c['sha256'];f=read(p.parent/'FROZEN.json');done=read(p.parent/'COMPLETED.json');cfg=f['config'];dp,ts=data_pool(s,cfg);assert ref(dp,'historical training data')==f['data_sha256'];assert len(ts)==done['training_tables']
  # Released data may differ in metadata serialization; check numerical training payloads.
  release=tables(s,'train');assert [t['table_id'] for t in ts]==[t['table_id'] for t in release]
  assert all(a['coordinates']==b['coordinates'] and a['labels']==b['labels'] for a,b in zip(ts,release))
  if s not in seen_data:
   seen_data[s]=dp
   for t in ts:datasets.append(dict(setting=s,table_id=t['table_id'],process_id=t['process_id'],family=t['family'],nodes=len(t['coordinates']),width_count=t['width_count'],coordinates_labels_sha256=hashlib.sha256(json.dumps([t['coordinates'],t['labels']]).encode()).hexdigest(),historical_data_sha256=sha(dp)))
  hist=replay(ts,seed,cfg['steps']);obs=sorted({k[3] for k in hist})
  for k,n in sorted(hist.items()):support_hist.append(dict(setting=s,training_seed=seed,stage='full_and_matched_controls_stage2',protocol=k[0],missing_ratio=k[1],nodes=k[2],observed_count=k[3],episodes=n,evidence='deterministic sampler-count reconstruction; no model execution'))
  base=dict(setting=s,seed=seed,steps=cfg['steps'],training_tables=len(ts),data_path=str(dp),data_sha256=sha(dp),node_counts=json.dumps(sorted({len(t['coordinates']) for t in ts})),observation_counts=json.dumps(obs),sampler='family then process then table; protocol; missing fraction .1/.3/.5/.7; width fold ignores ratio',low_budget_conditioning_training=(s=='public'),target_fit_steps=0)
  checkpoint_rows.append(dict(**base,method='full; pruned reuses same weights',role='confirmation',path=str(p),sha256=sha(p),frozen_path=str(p.parent/'FROZEN.json'),historical_log_last_step=done['history'][-1]['step'],hash_verified=True))
  for variant in ('residual','binary'):
   q=Path(PATHS['control_root'])/'runs'/f'{s}_{variant}_s{seed}'/'checkpoint.pt';fr=read(q.parent/'FROZEN.json');dd=read(q.parent/'COMPLETED.json');assert ref(q,'checkpoint')==dd['checkpoint_sha256']
   assert all(fr['config'][k]==cfg[k] for k in ('seed','steps','learning_rate','eta','span_weight','temperature'))
   assert ref(fr['config']['data'],'actual control training data')==sha(dp)
   assert dd['training_tables']==len(ts)
   for pathkey in ('init_from','scales_from'):
    assert ref(fr['config'][pathkey],'actual control initialization')==sha(ROOT/cfg[pathkey])
   checkpoint_rows.append(dict(**base,method=variant,role='confirmation',path=str(q),sha256=sha(q),frozen_path=str(q.parent/'FROZEN.json'),historical_log_last_step=dd['history'][-1]['step'],hash_verified=True))
  wp=ROOT/cfg['init_from'];wc=read(wp.parent/'config.json');wr=read(wp.parent/'result.json');assert ref(wp,'warm-start checkpoint')==wr['checkpoint_sha256'];assert wc['data_sha256']==sha(dp)
  wh=replay(ts,seed,wc['arguments']['steps'],width=False);wobs=sorted({k[3] for k in wh})
  for k,n in sorted(wh.items()):support_hist.append(dict(setting=s,training_seed=seed,stage='warm_start',protocol=k[0],missing_ratio=k[1],nodes=k[2],observed_count=k[3],episodes=n,evidence='deterministic sampler-count reconstruction; no model execution'))
  checkpoint_rows.append(dict(**(base|dict(steps=wc['arguments']['steps'],observation_counts=json.dumps(wobs),sampler='family/process/table; mcar/block/extrapolation; .1/.3/.5/.7')),method='warm_start',role='initialization of full and controls',path=str(wp),sha256=sha(wp),frozen_path=str(wp.parent/'config.json'),historical_log_last_step=wr['history'][-1]['step'],hash_verified=True))
for folder in ('learning','attention'):
 for p in sorted((R/folder).glob('*/checkpoint.pt')):
  fr=read(p.parent/'FROZEN.json');dd=read(p.parent/'COMPLETED.json');assert ref(p,'checkpoint')==dd['checkpoint_sha256'];s=fr.get('setting') or ('to_asap7' if p.parent.name.startswith('to_asap7') else 'reference');kind=fr.get('kind','attentioncap');chosen=selected[s][kind] if kind!='attentioncap' else att_sel[s];lr=fr.get('learning_rate',fr.get('lr'));seed=fr['seed'];used=lr==chosen['lr'];ts=tables(s,'train');assert fr['training_ids']==[t['table_id'] for t in ts]
  assert fr['code_sha256' if folder=='learning' else 'adapter_sha256']==sha(HERE/('learning.py' if folder=='learning' else 'attention.py'))
  ob=sorted({min(b,len(t['coordinates'])-1) for t in ts for b in (2,4,8,16,32,64)}) if kind=='cnp' else []
  checkpoint_rows.append(dict(setting=s,method=kind,seed=seed,steps=fr['steps'],training_tables=len(ts),data_path=str(ROOT/source_config(s)['data']),data_sha256=ref(ROOT/source_config(s)['data']),node_counts=json.dumps(sorted({len(t['coordinates']) for t in ts})),observation_counts=json.dumps(ob),sampler='mean-context CNP: uniform family/table, context sampled from 2/4/8/16/32/64 clipped n-1' if kind=='cnp' else 'direct MLP: same sampled split, context not input; loss on complement' if kind=='mlp' else 'direct geometry network: random table, 32 geometry training minibatch; not 32-context conditioning',low_budget_conditioning_training=kind=='cnp',target_fit_steps=chosen['adapt_steps'] if kind!='cnp' else 0,role='confirmation + validation' if used else 'validation-only LR candidate',path=str(p),sha256=sha(p),frozen_path=str(p.parent/'FROZEN.json'),hash_verified=True,observation_count_evidence='configured possible set; per-episode training supports not logged',learning_rate=lr))
rf=read(R/'reverse_transfer/FROZEN.json');rc=read(R/'reverse_transfer/selection.json')
assert rf['source_hash']==sha(HERE/'reverse_transfer.py')
for p in sorted((R/'reverse_transfer').glob('*.pt')):
 d=read(p.with_suffix('.json'));assert ref(p,'checkpoint')==d['checkpoint_sha256']
 checkpoint_rows.append(dict(setting='to_freepdk15',method='mlp',seed=d['seed'],steps=3000,training_tables=len(rf['train_ids']),data_path=str(seen_data['reference']),data_sha256=sha(seen_data['reference']),node_counts='[153]',observation_counts='[]',sampler='direct supervised regression; four families; entire chosen source table labels in loss',low_budget_conditioning_training=False,target_fit_steps=rc['adapt_steps'],role='confirmation + validation' if d['lr']==rc['lr'] else 'validation-only LR candidate',path=str(p),sha256=sha(p),frozen_path=str(R/'reverse_transfer/FROZEN.json'),hash_verified=True))
save('training_checkpoints.csv',checkpoint_rows);save('training_support_histogram.csv',support_hist);save('training_tables.csv',datasets)
# Small immutable attachments and original provenance references.
for name in ('FINAL_DECISION.md','CLAIM_EVIDENCE.csv'):
 p=ROOT/'docs/dac_characterization_20261114'/name;ref(p);shutil.copyfile(p,OUT/name)
p=ROOT/'paper/dac_revision_20261114/main.pdf';ref(p);shutil.copyfile(p,OUT/'main.pdf')
for p in [HERE/'EXPERIMENT_PLAN.yaml',ROOT/'unified/train.py',ROOT/'unified/episodes.py',ROOT/'pdkcap/train.py',ROOT/'pdkcap/sampling.py',ROOT/'experiments/paper_controls/run_controls.py',HERE/'learning.py',HERE/'attention.py',HERE/'reverse_transfer.py',R/'summary/native_artifact_manifest.json',ROOT/'docs/dac_characterization_20261114/DELIVERY_MANIFEST.json',R/'confirmation_public_failed_fork/FAILED.json',R/'downstream/queue_handoff_completed.json']:
 ref(p)
# Additional branch/profile timings stay descriptive; they are not decompositions of every confirmation call.
shutil.copyfile(R/'component_runtime_profile.csv',OUT/'component_runtime_profile.csv');ref(R/'component_runtime_profile.csv')
js('threshold_freeze.json',freezes)
js('provenance.json',dict(start_commit=BASE,observed_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_records_preserved=True,new_training=False,new_inference=False,new_field_solver=False,new_STA=False,checkpoint_count=len(checkpoint_rows),sampler_reconstruction='counts only, no encoders/models; historical per-episode counts were not logged',native_tie_rule='abs(diff)<=max(1e-12,1e-9*max(abs(a),abs(b)))',relative_difference='100*(Full-comparator)/abs(comparator); undefined for zero denominator',status='COMPLETION_ACCURACY_ONLY'))
save('input_references.csv',list(refs.values()))
print('Review data derived:',len(same),'budget cells;',len(trajectories),'threshold trajectories;',len(checkpoint_rows),'checkpoints;',len(nd),'downstream differences')
