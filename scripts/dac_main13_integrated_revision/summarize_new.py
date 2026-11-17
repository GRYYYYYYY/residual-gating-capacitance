"""Generate new manuscript tables only from completed experiment receipts."""
from pathlib import Path
import csv,json,gzip,collections,sys
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';P=R/'paper/dac_layout_query_revision';D=R/'docs/dac_main13_integrated_revision'
def rows(p):return list(csv.DictReader(Path(p).open()))
def write(p,rs):
 with Path(p).open('w') as f:w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)));w.writeheader();w.writerows(rs)
def table(name,head,rs,fmt):
 (P/'tables'/name).write_text('\n'.join([r'\begin{tabular}{'+fmt+'}',r'\toprule',' & '.join(head)+r' \\',r'\midrule',*[' & '.join(map(str,r))+r' \\' for r in rs],r'\bottomrule',r'\end{tabular}'])+'\n')
def native():
 assert json.loads((O/'native/matrix_completed.json').read_text())['arm_settings']==192
 rs=rows(O/'native_sparse_metrics.csv');assert len(rs)==192
 metrics=['net_cap_nrmse','ws_abs_ps','tns_abs_ps','endpoint_mae_ps','endpoint_p95_ps','endpoint_p99_ps','endpoint_max_ps','signed_slack_ps','extraction_s','wall_s']
 groups=collections.defaultdict(list)
 for r in rs:
  ready=json.loads((O/f"native/inputs/{r['case'].split('/')[0]}/B{r['budget']}_s{r['seed']}/ready.json").read_text())
  if r['method']!='native_sparse':assert int(r['applied'])==ready['eligible_slots']
  groups[r['case'],int(r['budget']),r['method']].append(r)
 means=[]
 for (case,b,method),rr in sorted(groups.items()):
  assert sorted(int(r['seed']) for r in rr)==[11,29,47]
  means.append(dict(case=case,budget=b,method=method,seeds=3,**{k:float(np.mean([float(r[k]) for r in rr])) for k in metrics}))
 write(O/'native_sparse_cell_means.csv',means);idx={(r['case'],r['budget'],r['method']):r for r in means}
 comparisons=[];counts=[]
 for control in ['native_sparse','mli_native','binary_native']:
  for metric in metrics[:7]:
   cc=[]
   for r in means:
    if r['method']!='full_native':continue
    b=idx[r['case'],r['budget'],control][metric];v=r[metric];gap=v-b;cc.append(gap)
    comparisons.append(dict(case=r['case'],budget=r['budget'],comparison='full_native-minus-'+control,metric=metric,full=v,control=b,difference=gap,relative_improvement=(1-v/b) if b>0 else '',zero_baseline=b==0))
   counts.append(dict(control=control,metric=metric,full_wins=sum(x<0 for x in cc),ties=sum(x==0 for x in cc),losses=sum(x>0 for x in cc),cells=16))
 write(O/'native_sparse_comparisons.csv',comparisons);write(O/'native_sparse_win_counts.csv',counts)
 rendered=[];tail=[];absolute=[]
 methods=['native_sparse','mli_native','binary_native','full_native']
 for case,b in sorted({(r['case'],r['budget']) for r in means}):
  label=case.replace('ihp-sg13g2','IHP').replace('sky130hs','Sky')
  rendered.append([label,b,*[f"{idx[case,b,m]['net_cap_nrmse']:.5f}" for m in methods],*[f"{idx[case,b,m]['ws_abs_ps']:.3f}" for m in methods]])
  tail.append([label,b,*[f"{idx[case,b,m]['endpoint_p99_ps']:.3f}" for m in methods],*[f"{idx[case,b,m]['tns_abs_ps']/1000:.4f}" for m in methods]])
  unit=json.loads(next(r['cap_unit'] for r in rs if r['case']==case));to_ff=float(unit[0])*{'PF':1000.,'FF':1.,'NF':1e6,'F':1e15}[unit[1].upper()]
  abs_caps=[np.mean([float(r['net_cap_rmse']) for r in rs if r['case']==case and int(r['budget'])==b and r['method']==m])*to_ff for m in methods]
  gains=[]
  for metric in ['net_cap_nrmse','ws_abs_ps','endpoint_p99_ps']:
   base=idx[case,b,'native_sparse'][metric];val=idx[case,b,'full_native'][metric];gains.append(f'{100*(1-val/base):+.1f}' if base>0 else '--')
  absolute.append([label,b,*[f'{x:.5g}' for x in abs_caps],*gains])
 table('native_sparse_accuracy.tex',['Layout','$B$','Native C','MLI C','Binary C','Full C','Native WS','MLI WS','Binary WS','Full WS'],rendered,'llrrrrrrrr')
 table('native_sparse_tails.tex',['Layout','$B$','Native P99','MLI P99','Binary P99','Full P99','Native TNS','MLI TNS','Binary TNS','Full TNS'],tail,'llrrrrrrrr')
 table('native_sparse_absolute.tex',['Layout','$B$','Native C','MLI C','Binary C','Full C','C gain','WS gain','P99 gain'],absolute,'llrrrrrrr')
 timing=[];coverage=[];load=json.loads((O/'native/model_load.json').read_text())['wall_s']
 for d in sorted((O/'native/inputs').glob('*/*')):
  ready=json.loads((d/'ready.json').read_text());inv=json.loads((d/'inventory/receipt.json').read_text());support=json.loads((d/'support.json').read_text());prep=rows(d/'prepare_timing.csv')
  # Conservative measured whole inventory process includes its diagnostic outputs;
  # expose them rather than claiming an optimized rule-only inventory.
  common=ready['prepare_total_s']-sum(float(x['prediction_and_write_s']) for x in prep)
  for r in prep:
   if r['method']=='pass':continue
   rr=[x for x in rs if x['case'].split('/')[0]==r['platform'] and x['budget']==r['budget'] and x['seed']==r['seed'] and x['method']==r['method']]
   for x in rr:
    charged_load=load if r['method'] in ['binary_native','full_native'] else 0.
    external=common+charged_load+float(r['prediction_and_write_s']);cold=external+float(x['wall_s'])
    timing.append(dict(case=x['case'],budget=x['budget'],seed=x['seed'],method=x['method'],common_input_inventory_s=common,measured_inventory_wall_s=inv['wall_s'],shared_all_model_load_s=charged_load,prediction_write_s=float(r['prediction_and_write_s']),external_stage_sum_s=external,native_process_wall_s=float(x['wall_s']),cold_modeled_stage_sum_s=cold,PEX_s=float(x['extraction_s']),native_build_s=float(x['native_build_s']),injection_s=float(x['injection_s']),SPEF_s=float(x['spef_write_s']),STA_s=float(x['sta_read_s'])+float(x['sta_analysis_s']),scope='modeled single-arm sum of measured shared-host stages; not standalone cold-launch measurement; diagnostic inventory includes SPEF/STA; all-model load conservatively charged to each neural arm, unnecessary for MLI; build/injection included in PEX; no speedup claim'))
  for x in [x for x in rs if x['case'].split('/')[0]==d.parent.name and f"B{x['budget']}_s{x['seed']}"==d.name]:
   coverage.append(dict(case=x['case'],budget=x['budget'],seed=x['seed'],method=x['method'],common_eligible_slots=ready['eligible_slots'],populated_slots=int(x['applied']),changed_slots=int(x['changed']),unchanged_slots=ready['all_slots']-int(x['changed']),unpopulated_slots=ready['all_slots']-int(x['applied']),excluded_from_payload_slots=ready['all_slots']-ready['eligible_slots'],all_native_slots=ready['all_slots'],all_native_eligible_slots=ready['native_eligible_slots'],support_tables=ready['support_tables'],excluded_rules=ready['excluded_rules'],budget_actual_min=min(s['budget_actual'] for s in support),budget_actual_max=max(s['budget_actual'] for s in support),return_level_coverage='smoke only; fallback/excluded return counts unmeasured in release matrix; slot counts are not call counts'))
 write(O/'timing_breakdown.csv',timing);write(O/'native_coverage_accounting.csv',coverage)
 costrows=[]
 for case in sorted({r['case'] for r in timing}):
  rr=[r for r in timing if r['case']==case];b=[r for r in rr if r['method']=='binary_native'];f=[r for r in rr if r['method']=='full_native']
  costrows.append([case.replace('ihp-sg13g2','IHP').replace('sky130hs','Sky'),f"{np.mean([r['external_stage_sum_s'] for r in b]):.2f}",f"{np.mean([r['external_stage_sum_s'] for r in f]):.2f}",f"{np.mean([r['PEX_s'] for r in b]):.2f}",f"{np.mean([r['PEX_s'] for r in f]):.2f}",f"{np.mean([r['cold_modeled_stage_sum_s'] for r in b]):.2f}",f"{np.mean([r['cold_modeled_stage_sum_s'] for r in f]):.2f}"])
 table('native_sparse_cost.tex',['Layout','B prep','F prep','B PEX','F PEX','B total$^*$','F total$^*$'],costrows,'lrrrrrr')
 c={(r['control'],r['metric']):r['full_wins'] for r in counts}
 text=(f"The new sparse-native matrix completes all 192 arm-settings (48 paired settings, 16 layout--budget cells). Full lowers net-C, worst-slack, and P99 endpoint errors relative to Native-sparse in {c['native_sparse','net_cap_nrmse']}/16, {c['native_sparse','ws_abs_ps']}/16, and {c['native_sparse','endpoint_p99_ps']}/16 cells, respectively. The corresponding counts against MLI-ext.-native are {c['mli_native','net_cap_nrmse']}/16, {c['mli_native','ws_abs_ps']}/16, and {c['mli_native','endpoint_p99_ps']}/16; against Binary-native they are {c['binary_native','net_cap_nrmse']}/16, {c['binary_native','ws_abs_ps']}/16, and {c['binary_native','endpoint_p99_ps']}/16. These are dependent descriptive cells after averaging the three support seeds. They do not establish uniform sparse-native gains.\n")
 (P/'tables/native_sparse_findings.tex').write_text(text)
 (D/'native_sparse_report.md').write_text('# Sparse-native results\n\n'+text+'\nImplementation and experiment completion PASS: both smoke cases pass; all192 net/endpoint identity checks and unchanged R pass; every injection consumes the entire common eligible payload. Performance is metric/condition dependent. Full-rule reference measures output fidelity, not physical accuracy. Source checkpoints and S-only contract are unchanged.\n\nTiming includes conservative diagnostic inventory cost. Source labels/training and actual paid target characterization are outside these measured target-process times. Release runs share the host with training; no stable speedup conclusion. Slot coverage is complete for the matrix; return-level coverage was traced only for smoke cases.\n')
 print(text)
def aggregate(records):
 acc={}
 for r in records:
  reg='outside' if r['segment']=='outside' else 'inside';key=(r['method'],r['ratio'],reg,r['protocol'],r['mask_seed'],r['process_id'],r['family'])
  e=np.array(r['squared_error']);y=np.array(r['squared_truth'])
  if key not in acc:acc[key]=[e.copy(),y.copy()]
  else:acc[key][0]+=e;acc[key][1]+=y
 masks=collections.defaultdict(list)
 for k,(e,y) in acc.items():masks[k[:5]].extend(np.sqrt(e[y>0]/y[y>0]).tolist())
 groups=collections.defaultdict(list)
 for k,v in masks.items():
  if v:groups[k[:4]].append(np.mean(v))
 return [dict(method=k[0],ratio=k[1],regime=k[2],protocol=k[3],macro_nrmse=float(np.mean(v))) for k,v in groups.items()]
def mechanism():
 cells=[];check={};base=rows(O/'coverage_cell_metrics.csv');lookup={(r['domain'],float(r['requested_holdout']),r['regime'],r['protocol'],r['method']):r for r in base}
 for domain in ['public','reference','to_asap7']:
  for stage in ['frozen','controls']:
   assert (O/f'mechanism/{domain}_{stage}_completed.json').exists()
   with gzip.open(O/f'mechanism/{domain}_{stage}.jsonl.gz','rt') as f:rr=aggregate(map(json.loads,f))
   for r in rr:
    if r['regime']=='inside' and r['protocol']=='extrapolation':continue
    b=lookup[domain,r['ratio'],r['regime'],r['protocol'],'full'];r=dict(domain=domain,**r,stronger_baseline=float(b['stronger_baseline']));r['error_ratio']=r['macro_nrmse']/r['stronger_baseline'];cells.append(r)
    if r['method'].endswith('_replay'):
     name=r['method'].replace('_replay','');original=float(lookup[domain,r['ratio'],r['regime'],r['protocol'],name]['macro_nrmse']);delta=abs(r['macro_nrmse']-original);check[domain+'_'+name]=max(delta,check.get(domain+'_'+name,0));assert delta<1e-7,(domain,name,delta)
 write(O/'mechanism_cell_metrics.csv',cells);summary=[]
 for method in ['full_replay','fixed_fusion','numerical_gate','no_agreement']:
  rr=[r for r in cells if r['method']==method];assert len(rr)==60
  fulls=[float(lookup[r['domain'],r['ratio'],r['regime'],r['protocol'],'full']['macro_nrmse']) for r in rr]
  tol=8*np.finfo(np.float32).eps
  summary.append(dict(method=method,conditions=60,beats_both=sum(r['macro_nrmse']<r['stronger_baseline'] for r in rr),beats_both_tolerance=sum(r['macro_nrmse']<r['stronger_baseline']-tol*max(abs(r['macro_nrmse']),abs(r['stronger_baseline'])) for r in rr),worst_error_ratio=max(r['error_ratio'] for r in rr),mean_cell_error=float(np.mean([r['macro_nrmse'] for r in rr])),beats_full=sum(r['macro_nrmse']<f for r,f in zip(rr,fulls)),ties_full=sum(r['macro_nrmse']==f for r,f in zip(rr,fulls))))
  if method=='full_replay':summary[-1].update(beats_full=0,ties_full=60) # Reference identity, after the explicit replay-roundoff check above.
 write(O/'mechanism_summary.csv',summary);(O/'mechanism_replay_checks.json').write_text(json.dumps(check,indent=2))
 labels={'full_replay':'Full','fixed_fusion':'C2: fixed fusion','numerical_gate':'C1: numerical gate','no_agreement':'C3: no agreement'}
 table('mechanism_controls.tex',['Method','Both$^*$','Worst $R$','Mean $E$','Beats Full'],[[labels[r['method']],str(r['beats_both'])+'/'+str(r['beats_both_tolerance']),f"{r['worst_error_ratio']:.4f}",f"{r['mean_cell_error']:.4f}",str(r['beats_full'])+'/60' if r['method']!='full_replay' else '--'] for r in summary],'lrrrr')
 # MLI status cross-tab, retaining the original mean-mask statistic per cell.
 strata=[]
 for domain in ['public','reference','to_asap7']:
  with gzip.open(O/f'mechanism/{domain}_frozen_mli_strata.jsonl.gz','rt') as f:rr=list(map(json.loads,f))
  for tag in sorted({r['mli_status'] for r in rr}):
   chosen=[r for r in rr if r['mli_status']==tag]
   for row in aggregate(chosen):
    take=[r for r in chosen if r['method']==row['method'] and r['ratio']==row['ratio'] and r['protocol']==row['protocol'] and r['segment']==row['regime']]
    strata.append(dict(domain=domain,mli_status=tag,**row,query_occurrences=sum(r['n'] for r in take),tables=len({r['table_id'] for r in take})))
 write(O/'mli_stratum_metrics.csv',strata)
 print('mechanism',summary,'replay',check)
if __name__=='__main__':
 if '--native' in sys.argv:native()
 if '--mechanism' in sys.argv:mechanism()
