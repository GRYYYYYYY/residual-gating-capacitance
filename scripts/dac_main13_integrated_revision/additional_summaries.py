"""Derived pairing, batching, coverage and reuse summaries; never run experiments."""
from pathlib import Path
import csv,json,collections,hashlib
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';P=R/'paper/dac_layout_query_revision'
def read(p):return list(csv.DictReader(p.open()))
def write(p,rows):
 with p.open('w') as f:w=csv.DictWriter(f,list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
coverage_cells=read(O/'coverage_cell_metrics.csv');near=[];uncertainty=[]
for method in ['residual','binary','full']:
 rr=[r for r in coverage_cells if r['method']==method];successful=[r for r in rr if float(r['error_ratio'])<1]
 near.extend(dict(r,selection='five smallest positive margins; deterministic descending ratio, then domain/regime/protocol/holdout') for r in sorted(successful,key=lambda r:(-float(r['error_ratio']),r['domain'],r['regime'],r['protocol'],float(r['requested_holdout'])))[:5])
 uncertainty.append(dict(method=method,conditions=60,point_improvements=len(successful),point_regressions=sum(float(r['error_ratio'])>1 for r in rr),improvement_intervals_cross_zero=sum(float(r['paired_gap_ci_low'])<=0<=float(r['paired_gap_ci_high']) for r in successful),regression_intervals_cross_zero=sum(float(r['paired_gap_ci_low'])<=0<=float(r['paired_gap_ci_high']) for r in rr if float(r['error_ratio'])>1),interpretation='paired group-bootstrap intervals; small FEM/transfer groups; dependent cells; counts are descriptive, no multiplicity-adjusted significance or safety probability'))
write(O/'near_regression_successes.csv',near);write(O/'baseline_uncertainty_summary.csv',uncertainty)
report=R/'docs/dac_main13_integrated_revision/baseline_consistency_report.md'
text=report.read_text().split('\n## Nearest successful')[0].split('\nNearest successful cases')[0]
lines=['','## Nearest successful conditions and interval uncertainty','','Five smallest positive margins per variant are retained in near_regression_successes.csv; no conditions are removed.']
for method,label in [('residual','Ungated'),('binary','Binary'),('full','Full')]:
 r=next(r for r in near if r['method']==method);u=next(r for r in uncertainty if r['method']==method)
 lines.append(f"- {label}: nearest success {r['domain']}/{r['regime']}/{r['protocol']}/{r['requested_holdout']}, margin {100*float(r['improvement_margin']):.6f}%, paired gap interval [{float(r['paired_gap_ci_low']):.8f},{float(r['paired_gap_ci_high']):.8f}]. Intervals cross zero in {u['improvement_intervals_cross_zero']}/{u['point_improvements']} improved cells and {u['regression_intervals_cross_zero']}/{u['point_regressions']} regressed cells.")
lines+=['','These are correlated exploratory interval counts, not independent tests or a multiple-comparison guarantee. FEM/transfer still have only4/2 groups.']
report.write_text(text+'\n'.join(lines)+'\n')
rs=read(O/'native_sparse_metrics.csv');assert len(rs)==192
means=read(O/'native_sparse_cell_means.csv');rng=np.random.default_rng(20261117)
idx={(r['case'],r['budget'],r['seed'],r['method']):r for r in rs};paired=[];intervals=[]
for control in ['native_sparse','mli_native','binary_native']:
 for metric in ['net_cap_nrmse','ws_abs_ps','tns_abs_ps','endpoint_mae_ps','endpoint_p95_ps','endpoint_p99_ps','endpoint_max_ps']:
  blocks=collections.defaultdict(list)
  for case,b in sorted({(r['case'],r['budget']) for r in rs}):
   diffs=[float(idx[case,b,s,'full_native'][metric])-float(idx[case,b,s,control][metric]) for s in ['11','29','47']]
   paired.append(dict(case=case,budget=b,control=control,metric=metric,mean_paired_gap=np.mean(diffs),min_seed_gap=min(diffs),max_seed_gap=max(diffs),seed_gaps=json.dumps(diffs),independent_units='layout nested in process; seeds are dependent support repeats'))
   blocks[case.split('/')[0]].append(np.mean(diffs))
  bm=np.array([np.mean(x) for x in blocks.values()]);boot=bm[rng.integers(0,len(bm),(10000,len(bm)))].mean(1);lo,hi=np.quantile(boot,[.025,.975])
  intervals.append(dict(control=control,metric=metric,mean_paired_gap=bm.mean(),low95=lo,high95=hi,process_clusters=len(bm),resamples=10000,seed=20261117,interpretation='descriptive four-process cluster bootstrap; not reliable population significance, layouts/budgets/seeds stay together'))
write(O/'native_sparse_paired_seed_ranges.csv',paired);write(O/'native_sparse_cluster_intervals.csv',intervals)
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':8,'pdf.fonttype':42})
fig,axs=plt.subplots(1,3,figsize=(7.2,4.0),sharey=True)
ix={(r['case'],r['budget'],r['method']):r for r in means};cells=sorted({(r['case'],r['budget']) for r in means},reverse=True)
for ax,metric,title in zip(axs,['net_cap_nrmse','ws_abs_ps','endpoint_p99_ps'],['Net capacitance','Worst slack','Endpoint P99']):
 for method,color,marker in [('binary_native','#e1812c','x'),('full_native','#2866a5','o')]:
  gains=[]
  for case,b in cells:
   v=float(ix[case,b,method][metric]);base=float(ix[case,b,'native_sparse'][metric]);gains.append(100*(1-v/base) if base else np.nan)
  ax.scatter(gains,np.arange(len(cells)),s=18,color=color,marker=marker,label=method.split('_')[0].title())
 ax.axvline(0,color='black',lw=.6);ax.grid(axis='x',alpha=.2);ax.set(title=title)
axs[0].set_yticks(range(len(cells)),[c.replace('ihp-sg13g2','IHP').replace('sky130hs','Sky')+' B'+b for c,b in cells]);axs[-1].legend(loc='lower left',fontsize=7);fig.supxlabel('Error reduction from Native-sparse (%)',fontsize=8);fig.tight_layout()
for ext in ['pdf','png']:fig.savefig(P/f'figures/native_sparse_tradeoffs.{ext}',dpi=180,bbox_inches='tight')
batch=read(O/'query_batching.csv');out=[]
for domain in ['public','reference','to_asap7']:
 for method in ['full','binary','residual']:
  rr=[r for r in batch if r['domain']==domain and r['method']==method]
  for r in rr:
   ref=next(a for a in rr if a['case']==r['comparison_to']);e=float(r['source_scaled_reference_error']);e0=float(ref['source_scaled_reference_error'])
   out.append(dict(domain=domain,method=method,case=r['case'],absolute_change=r['absolute_change'],source_scaled_change=r['source_scaled_change'],baseline_scaled_error=e0,perturbed_scaled_error=e,signed_maxnorm_error_change=e-e0,error_ratio=(e/e0 if e0 else ''),zero_baseline_error=e0==0))
write(O/'query_batching_error_changes.csv',out)
timing=read(O/'timing_breakdown.csv');reuse=[]
for r in timing:
 for n in [1,10,100]:
  prep=float(r['external_stage_sum_s']);path=float(r['native_process_wall_s'])
  reuse.append(dict(case=r['case'],budget=r['budget'],seed=r['seed'],method=r['method'],N_reuse=n,reusable_measured_stage_sum_s=prep,per_design_process_s=path,modeled_total_s=prep+n*path,scope='N=10/100 modeled repeats with identical rule/S/model/canonical-Q payload; only AES-to-Ibex payload reuse actually exercised; every native process pays build/injection; diagnostic inventory charged once; no claim for changed library/support or arbitrary designs'))
write(O/'native_reuse_cost_model.csv',reuse)
coverage=read(O/'native_coverage_accounting.csv');cov=[]
for platform in ['asap7','gf180','ihp-sg13g2','sky130hs']:
 for b in ['4','8']:
  rr=[r for r in coverage if r['case']==platform+'/aes' and r['budget']==b and r['method']=='full_native']
  cov.append(dict(platform=platform,budget=b,affected_rules=rr[0]['support_tables'],excluded_rules=rr[0]['excluded_rules'],actual_support_min=min(int(r['budget_actual_min']) for r in rr),actual_support_max=max(int(r['budget_actual_max']) for r in rr),eligible_slots_min=min(int(r['common_eligible_slots']) for r in rr),eligible_slots_max=max(int(r['common_eligible_slots']) for r in rr),changed_slots_min=min(int(r['changed_slots']) for r in rr),changed_slots_max=max(int(r['changed_slots']) for r in rr),native_slots_min=min(int(r['all_native_slots']) for r in rr),native_slots_max=max(int(r['all_native_slots']) for r in rr)))
write(O/'native_coverage_summary.csv',cov)
# Reuse the existing 30% numerical-control protocol, checking raw accumulators.
import runpy
aggregate=runpy.run_path(str(R/'scripts/verify_final_paper.py'))['aggregate']
fixed=read(P/'tables/fixed_missingness.csv');rendered=[];diffs=[]
for domain in ['public','reference','to_asap7']:
 base=R/'experiments/paper_controls/scores'/domain
 raw=aggregate(base/'baseline_confirmation.jsonl.gz');learned=aggregate(base/'learned_confirmation.jsonl.gz');affine=aggregate(base/'affine_confirmation.jsonl.gz')
 selected=json.loads((base/'affine_selection.json').read_text())['selected']
 for r in [r for r in fixed if r['domain']==domain]:
  for method in ['gp','pchip','idw']:
   v=next(v for (m,seed,cond),v in raw.items() if m==method and cond==r['condition']);delta=abs(v-float(r[method]));assert delta<1e-12;diffs.append(delta)
  assert abs(affine[selected,'ensemble',r['condition']]-float(r['affine']))<1e-12
  for method in ['full','binary','residual']:
   assert abs(learned['full_replayed' if method=='full' else method,'ensemble',r['condition']]-float(r[method]))<1e-12
  label=r['condition'].replace('outside/extrapolation','Boundary').replace('inside','In').replace('outside','Out').replace('mcar','random')
  rendered.append([{'public':'Public','reference':'FEM','to_asap7':'Transfer'}[domain],label,*[f'{float(r[m]):.4f}' for m in ['anchor','affine','gp','pchip','idw','residual','binary','full']]])
tex='\n'.join([r'\begin{tabular}{llrrrrrrrr}',r'\toprule',r'Domain & Queries & Anchor & Affine & RBF-GP & PCHIP & IDW & Ungated & Binary & Full \\',r'\midrule',*[' & '.join(r)+r' \\' for r in rendered],r'\bottomrule',r'\end{tabular}'])+'\n'
(P/'tables/numerical_30percent.tex').write_text(tex)
(O/'numerical_control_reuse_checks.json').write_text(json.dumps(dict(status='PASS',protocol='existing 30% holdout numerical controls; unchanged mean-mask NRMSE; not a new optimized 60-condition baseline',cells=15,max_reaggregation_delta=max(diffs)),indent=2))
if (O/'input_sealing_timing.csv').exists():
 seals={(r['platform'],r['budget'],r['seed']):r for r in read(O/'input_sealing_timing.csv')};out=[]
 for r in rs:
  if r['method']!='native_sparse':continue
  seal=seals[r['case'].split('/')[0],r['budget'],r['seed']]
  out.append(dict(case=r['case'],budget=r['budget'],seed=r['seed'],measured_native_process_s=r['wall_s'],isolated_input_release_s=seal['input_sealing_wall_s'],modeled_total_s=float(r['wall_s'])+float(seal['input_sealing_wall_s']),scope='measured original sparse native process + later isolated warm-cache input-release timing; not a measured cold launch; native sparse does not require injection inventory or neural checkpoints'))
 write(O/'native_sparse_base_cost_model.csv',out)
 costrows=[]
 for method,label in [('native_sparse','Native-sparse'),('mli_native','MLI-ext.-native'),('binary_native','Binary-native'),('full_native','Full-native')]:
  values=[]
  for n in [1,10,100]:
   if method=='native_sparse':values.append(np.mean([float(r['isolated_input_release_s'])/n+float(r['measured_native_process_s']) for r in out]))
   else:values.append(np.mean([float(r['external_stage_sum_s'])/n+float(r['native_process_wall_s']) for r in timing if r['method']==method]))
  costrows.append([label,*[f'{v:.2f}' for v in values]])
 (P/'tables/native_reuse_cost.tex').write_text('\n'.join([r'\begin{tabular}{lrrr}',r'\toprule',r'Method & $N=1$ & $N=10$ & $N=100$ \\',r'\midrule',*[' & '.join(r)+r' \\' for r in costrows],r'\bottomrule',r'\end{tabular}'])+'\n')
print('additional summaries complete',len(paired),'cell contrasts',len(intervals),'four-process intervals')
if (O/'physical_behavior.csv').exists():
 physical=read(O/'physical_behavior.csv');contexts=0;support_ranges=[]
 for p in (O/'native/inputs').glob('*/*/support.json'):
  supports=json.loads(p.read_text());byctx={s['context_key']:s for s in supports}
  for s in supports:
   x=np.asarray(s['S_coordinates']);assert np.array_equal(x[:,1],x[:,2]);contexts+=1
  scale=2000 if p.parent.parent.name=='gf180' else 1000;n=outside=0
  for line in (p.parent/'full_native.tsv').read_text().splitlines():
   parts=line.split()[0].split('|');s=byctx['|'.join(parts[:7])];d=int(parts[8])/scale;low=min(x[1] for x in s['S_coordinates']);high=max(x[1] for x in s['S_coordinates']);n+=1;outside+=not(low<=d<=high)
  assert outside==0;support_ranges.append(dict(platform=p.parent.parent.name,setting=p.parent.name,slots=n,outside_S_distance_range=outside))
 (O/'tests/native_slot_support_ranges.json').write_text(json.dumps(dict(status='PASS',checks=sorted(support_ranges,key=lambda r:(r['platform'],r['setting'])),meaning='populated represented coordinates are within available S distance range; component/native units separately checked'),indent=2))
 (O/'tests/symmetric_context_checks.json').write_text(json.dumps(dict(status='PASS',support_contexts=contexts,equal_left_right_scalar_projection=True,scope='evaluated native S/Q symmetric scalar contexts; not arbitrary asymmetric geometry or universal monotonicity'),indent=2))
 (O/'tests/adjacent_slot_diagnostics.json').write_text(json.dumps(dict(status='PASS',methods={m:dict(max_source_scaled_jump=max(float(r['max_adjacent_source_scaled_jump'] or 0) for r in physical if r['method']==m),jumps_above_one_source_scale=sum(int(r['jumps_above_one_source_scale']) for r in physical if r['method']==m)) for m in ['mli_native','binary_native','full_native']},interpretation='descriptive, not a physical smoothness certificate; protected S bins excluded from adjacent-slot pairs'),indent=2))
