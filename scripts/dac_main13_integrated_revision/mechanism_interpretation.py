"""Post-hoc diagnostic case selection and MLI strata, independent of prediction."""
from pathlib import Path
import csv,json,gzip,collections
import numpy as np
from summarize_new import aggregate,table
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';M=O/'mechanism';P=R/'paper/dac_layout_query_revision'
def rows(p):return list(csv.DictReader(p.open()))
def write(p,rs):
 with p.open('w') as f:w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)));w.writeheader();w.writerows(rs)
base=rows(O/'coverage_cell_metrics.csv');cells={}
for r in base:
 key=(r['domain'],r['regime'],r['protocol'],float(r['requested_holdout']));cells.setdefault(key,{})[r['method']]=r
selected=collections.defaultdict(list)
for domain in ['public','reference','to_asap7']:
 keys=sorted(k for k in cells if k[0]==domain)
 selected[max(keys,key=lambda k:float(cells[k]['full']['error_ratio']))].append('smallest Full margin')
 for method in ['residual','binary']:
  selected[max(keys,key=lambda k:float(cells[k][method]['error_ratio']))].append('worst '+method+' ratio')
  selected[max(keys,key=lambda k:float(cells[k]['full']['macro_nrmse'])-float(cells[k][method]['macro_nrmse']))].append('largest '+method+' absolute advantage over Full')
assert (M/'candidate_scoring_completed.json').exists()
candidate=rows(O/'mechanism_candidate_metrics.csv');simple=rows(O/'mechanism_simplified_diagnostics.csv');names=json.loads((M/'public_frozen_completed.json').read_text())['candidate_order'];out=[];support=collections.defaultdict(list)
for domain in ['public','reference','to_asap7']:
 with gzip.open(M/f'{domain}_candidate_outputs.jsonl.gz','rt') as f:
  for r in map(json.loads,f):
   if 'candidate' not in r or r['member']!=0:continue
   for reg in ['inside','outside']:
    k=(domain,reg,r['protocol'],r['ratio'])
    n=sum((s==0)==(reg=='outside') for s in r['segment'])
    if k in selected and n:support[k].append((r['n_support'],r['support_affine_rank'],n))
for key,reasons in sorted(selected.items()):
 domain,reg,proto,ratio=key
 meta=dict(domain=domain,regime=reg,protocol=proto,ratio=ratio,selection='; '.join(reasons),**{m:float(cells[key][m]['macro_nrmse']) for m in ['full','binary','residual']},stronger_baseline=float(cells[key]['full']['stronger_baseline']))
 ss=support[key];meta.update(support_min=min(s[0] for s in ss),support_max=max(s[0] for s in ss),support_episode_mean=np.mean([s[0] for s in ss]),support_ranks=json.dumps(dict(collections.Counter(s[1] for s in ss))),query_occurrences=sum(s[2] for s in ss))
 rr=[r for r in candidate if r['domain']==domain and r['regime']==reg and r['protocol']==proto and float(r['ratio'])==ratio]
 diagnostic=[]
 for e,name in enumerate(names):
  x=[r for r in rr if int(r['candidate_index'])==e];n=sum(int(r['valid_query_occurrences']) for r in x);sse=sum(float(r['candidate_SSE']) for r in x);anchor=sum(float(r['anchor_SSE']) for r in x)
  diagnostic.append(dict(candidate=name,valid_component_occurrences=n,pooled_SSE_ratio_to_anchor=sse/anchor if anchor else None,mean_valid_weight=sum(float(r['mean_weight'] or 0)*int(r['valid_query_occurrences']) for r in x)/n if n else None,correct_direction_fraction=sum(float(r['correct_direction_fraction'] or 0)*int(r['valid_query_occurrences']) for r in x)/n if n else None))
 for method in ['residual','binary']:
  x=[r for r in simple if r['domain']==domain and r['regime']==reg and r['protocol']==proto and float(r['ratio'])==ratio and r['method']==method];n=sum(int(r['query_occurrences']) for r in x)
  for field in ['wrong_direction_fraction','overcorrecting_fraction','mean_alpha']:meta[method+'_'+field]=sum(float(r[field])*int(r['query_occurrences']) for r in x)/n
  own=sum(float(r['own_ungated_candidate_SSE']) for r in x);pred=sum(float(r['prediction_SSE']) for r in x);meta[method+'_gate_SSE_ratio_to_own_ungated']=pred/own if own else None
 meta['candidate_diagnostics']=json.dumps(diagnostic);out.append(meta)
write(O/'mechanism_selected_cases.csv',out)
# Complete-cell / sparse-cell / boundary strata with original per-cell weighting.
strata=[];exposure=[];frozen=[];mli_deltas={};status_differences=[]
for domain in ['public','reference','to_asap7']:
 with gzip.open(M/f'{domain}_frozen.jsonl.gz','rt') as f:frozen.extend(dict(domain=domain,**r) for r in aggregate(map(json.loads,f)) if not (r['regime']=='inside' and r['protocol']=='extrapolation'))
 with gzip.open(M/f'{domain}_frozen_mli_strata.jsonl.gz','rt') as f:records=list(map(json.loads,f))
 mli_records=[r for r in records if r['method']=='mli_sparse']
 dd=[]
 for r in aggregate(mli_records):
  key=(domain,r['regime'],r['protocol'],r['ratio'])
  if key in cells:dd.append(abs(r['macro_nrmse']-float(cells[key]['mli_sparse']['macro_nrmse'])))
 assert max(dd)<1e-12;mli_deltas[domain]=max(dd)
 counts=collections.Counter()
 for r in mli_records:
  if r['mli_status']=='complete_cell':counts[r['table_id'],r['protocol'],float(r['ratio']),int(r['mask_seed'])]+=r['n']
 for r in rows(R/f'results/pex_kernel_revision/coverage_inventory_{domain}.csv'):
  key=r['table_id'],r['protocol'],float(r['requested_holdout']),int(r['seed'])
  if counts[key]!=int(r['complete_cell_queries']):status_differences.append(dict(domain=domain,table_id=r['table_id'],protocol=r['protocol'],ratio=r['requested_holdout'],seed=r['seed'],archived_complete=int(r['complete_cell_queries']),replayed_complete=counts[key],support_count=r['support_count'],query_count=r['query_count']))
 for tag in sorted({r['mli_status'] for r in records}):
  take=[r for r in records if r['mli_status']==tag]
  for r in aggregate(take):
   if r['regime']=='inside' and r['protocol']=='extrapolation':continue
   strata.append(dict(domain=domain,mli_status=tag,**r))
  for reg in ['inside','outside']:
   sub=[r for r in take if r['method']=='mli_sparse' and r['segment']==reg];exposure.append(dict(domain=domain,status=tag,regime=reg,query_occurrences=sum(r['n'] for r in sub),tables=len({r['table_id'] for r in sub})))
write(O/'mechanism_frozen_cells.csv',frozen);write(O/'mli_strata_cells.csv',strata);write(O/'mli_strata_exposure.csv',exposure)
summary=[]
for domain in ['public','reference','to_asap7']:
 for tag in sorted({r['mli_status'] for r in strata if r['domain']==domain}):
  for reg in ['inside','outside']:
   rr=[r for r in strata if r['domain']==domain and r['mli_status']==tag and r['regime']==reg];ix={(r['ratio'],r['protocol'],r['method']):r['macro_nrmse'] for r in rr};keys=sorted({(r['ratio'],r['protocol']) for r in rr})
   if not keys:continue
   e=next(x for x in exposure if x['domain']==domain and x['status']==tag and x['regime']==reg)
   vals={m:np.mean([ix[a,b,m] for a,b in keys]) for m in ['mli_sparse','full_replay','binary_replay','residual_replay']}
   summary.append(dict(domain=domain,status=tag,regime=reg,conditions=len(keys),query_occurrences=e['query_occurrences'],tables=e['tables'],**vals,full_beats_mli=sum(ix[a,b,'full_replay']<ix[a,b,'mli_sparse'] for a,b in keys)))
write(O/'mli_strata_summary.csv',summary)
table('mli_strata.tex',['Domain','Status','Region','Queries','MLI','Ungated','Binary','Full'],[[{'public':'Public','reference':'FEM','to_asap7':'Transfer'}[r['domain']],{'complete_cell':'Complete cell','explicit_clamp':'Clamp','sparse_support_extension':'Sparse extension'}[r['status']],r['regime'],r['query_occurrences'],*[f'{r[m]:.4f}' for m in ['mli_sparse','residual_replay','binary_replay','full_replay']]] for r in summary],'lllrrrrr')
old=json.loads((O/'coverage_checks.json').read_text())['checks'];old_complete=sum(r['complete_cell_queries'] for r in old.values());new_complete=sum(r['query_occurrences'] for r in exposure if r['status']=='complete_cell');total=sum(r['all_queries'] for r in old.values())
assert sum(r['query_occurrences'] for r in exposure)==total
ids={r['table_id'] for r in status_differences};cfg=json.loads((R/'configs/paper_models.json').read_text())
ts={r['table_id']:r for r in map(json.loads,(R/cfg['public']['cohort']).read_text().splitlines())}
assert len(status_differences)==120 and len(ids)==2 and all(len(ts[i]['coordinates'])==2 and not np.asarray(ts[i]['labels']).any() for i in ids)
assert all(r['support_count']=='1' and r['query_count']=='1' and r['archived_complete']==1 and r['replayed_complete']==0 for r in status_differences)
write(O/'mli_status_reclassification.csv',status_differences)
(O/'mli_status_reconciliation.json').write_text(json.dumps(dict(status='PASS',archived_complete=old_complete,replayed_complete=new_complete,all_queries=total,archived_percent=100*old_complete/total,corrected_percent=100*new_complete/total,mli_error_reaggregation_max_delta=mli_deltas,explanation='120 single-support requests from two all-zero two-node Public tables: archived inventory says complete_cell; current explicit constant-axis boundary test says clamp. Values remain zero and all condition MLI errors reproduce; original inventory is retained, only status counts corrected.'),indent=2))
(P/'tables/coverage_findings.tex').write_text(r'Figure~\ref{fig:coverage} includes all 60 domain--holdout--condition cells. Full has lower error than the OpenRCX kernel, MLI-ext., and Binary in 60, 60, and 49 cells, respectively. The kernels share 21,840 feasible support/query episodes. Complete MLI cells cover '+f'{100*new_complete/total:.2f}'+r'\% of query occurrences after explicit boundary-status reconciliation; the remainder use the declared boundary or sparse-support extension. The inventory flags 11,245 repeated rounded S/Q episodes, which are not additional independent evidence. Full numerical controls are retained.'+'\n')
(O/'mechanism_diagnostic_checks.json').write_text(json.dumps(dict(status='PASS',selected_cases=len(out),selection='all-domain min Full margin, worst simplified ratio, largest absolute simplified advantage; lexical tie order; full60 scored, no condition dropped',candidate_metric='pooled query-occurrence SSE ratios within valid candidate support; not the Fig4 macro metric; no causal inference from weight',MLI_summary='mean of available mean-mask macro condition errors inside each status/region; exposure counts preserve repeated masks'),indent=2))
print('mechanism cases',len(out),'MLI strata',len(summary))
