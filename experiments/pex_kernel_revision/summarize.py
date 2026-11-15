from common import *
import gzip,collections,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=R/'paper/dac_layout_query_revision';T=P/'tables';F=P/'figures'
LABEL={'mli_sparse':'MLI + sparse extension','mli':'Specified MLI','openrcx_kernel':'OpenRCX kernel','openrcx_ideal':'Ideal distance LI','binary':'Binary','full':'Full','binary_compute':'Binary compute table','full_compute':'Full compute table','anchor':'Anchor','numerical_only':'Selected GP'}
COLOR={'mli_sparse':'#777777','mli':'#777777','openrcx_kernel':'#46816d','binary':'#176394','full':'#b34332'}
def table(name,heads,rows,fmt):
 (T/(name+'.tex')).write_text('\\begin{tabular}{'+fmt+'}\n\\toprule\n'+' & '.join(heads)+r' \\'+'\n\\midrule\n'+'\n'.join(' & '.join(map(str,r))+r' \\' for r in rows)+'\n\\bottomrule\n\\end{tabular}\n')
def save(fig,name):
 for ext in ['pdf','png']:fig.savefig(F/(name+'.'+ext),bbox_inches='tight',dpi=180)
 plt.close(fig)
def coverage():
 inventory=[];scores=[]
 for domain in ['public','reference','to_asap7']:
  inv=list(csv.DictReader((O/f'coverage_inventory_{domain}.csv').open()));inventory.extend(inv);valid={r['SQ_hash'] for r in inv if r['openrcx_applicable']=='True'}
  # Keep both the all-S/Q coverage study and the common applicable population.
  acc=collections.defaultdict(lambda:[None,None])
  with gzip.open(O/f'coverage_{domain}.jsonl.gz','rt') as f:
   for l in f:
    r=json.loads(l)
    if r['segment']=='all':continue
    reg='complete_cell' if r['segment']=='complete_cell' else 'outside' if r['segment']=='outside' else 'inside'
    for pop in ['all','common'] if r['SQ_hash'] in valid else ['all']:
     key=(pop,r['method'],r['ratio'],reg,r['protocol'],r['mask_seed'],r['process_id'],r['family']);v=acc[key];e=np.array(r['squared_error']);y=np.array(r['squared_truth']);v[0]=e if v[0] is None else v[0]+e;v[1]=y if v[1] is None else v[1]+y
  masks=collections.defaultdict(list)
  for key,(e,y) in acc.items():masks[key[:6]].extend(np.sqrt(e[y>0]/y[y>0]).tolist())
  groups=collections.defaultdict(list)
  for key,vals in masks.items():
   if vals:groups[key[:5]].append(float(np.mean(vals)))
  for (pop,m,ratio,reg,protocol),vals in groups.items():scores.append(dict(domain=domain,population=pop,method=m,requested_holdout=ratio,regime=reg,protocol=protocol,macro_nrmse=float(np.mean(vals)),mask_count=len(vals)))
 csvwrite(O/'support_coverage_inventory.csv',inventory)
 detailed=[]
 for row in scores:
  ii=[a for a in inventory if a['domain']==row['domain'] and a['protocol']==row['protocol'] and float(a['requested_holdout'])==row['requested_holdout'] and (row['population']=='all' or a['openrcx_applicable']=='True')]
  field='complete_cell_queries' if row['regime']=='complete_cell' else 'inside_count' if row['regime']=='inside' else 'outside_count'
  detailed.append(dict(row,episodes=len(ii),tables=len({a['table_id'] for a in ii}),query_count=sum(int(a[field]) for a in ii),support_sum_over_episodes=sum(int(a['support_count']) for a in ii),all_query_count=sum(int(a['query_count']) for a in ii),complete_cell_queries=sum(int(a['complete_cell_queries']) for a in ii),sparse_extension_queries=sum(int(a['sparse_extension_queries']) for a in ii),duplicate_episodes=sum(a['duplicate_of']!='null' for a in ii),effective_ranks=','.join(sorted({a['rank'] for a in ii}))))
 csvwrite(O/'support_coverage_results.csv',detailed);csvwrite(O/'support_coverage_scores.csv',scores)
 plt.rcParams.update({'font.size':8,'font.family':'DejaVu Sans','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
 cond=[('inside','mcar','In/random'),('inside','block','In/block'),('outside','mcar','Out/random'),('outside','block','Out/block'),('outside','extrapolation','Boundary')]
 fig,axs=plt.subplots(3,5,figsize=(7.1,4.5),sharex=True);fig.subplots_adjust(left=.085,right=.99,bottom=.11,top=.88,wspace=.36,hspace=.42)
 for i,(domain,title) in enumerate([('public','Public'),('reference','FEM'),('to_asap7','Transfer')]):
  fullrows=[]
  for j,(reg,proto,cl) in enumerate(cond):
   for m in ['mli_sparse','openrcx_kernel','binary','full']:
    rr=sorted([r for r in scores if r['domain']==domain and r['population']=='common' and r['method']==m and r['regime']==reg and r['protocol']==proto],key=lambda r:r['requested_holdout'])
    axs[i,j].plot([100*r['requested_holdout'] for r in rr],[r['macro_nrmse'] for r in rr],linestyle='--' if m=='openrcx_kernel' else '-',marker={'openrcx_kernel':'^','mli_sparse':'v','binary':'o','full':'s'}[m],color=COLOR[m],label=LABEL[m],lw=1,ms=3)
   axs[i,j].set_yscale('log');axs[i,j].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter());axs[i,j].tick_params(labelsize=8);axs[i,j].set_xticks([10,30,50,70]);axs[i,j].grid(alpha=.15)
   if i==0:axs[i,j].set_title(cl,fontsize=8)
   if j==0:axs[i,j].set_ylabel(title+' NRMSE',fontsize=8)
   for ratio in [.1,.3,.5,.7]:
    row=[cl,str(int(ratio*100))]
    for m in ['openrcx_kernel','mli_sparse','anchor','numerical_only','binary','full']:
     rr=[r for r in scores if r['domain']==domain and r['population']=='common' and r['method']==m and r['regime']==reg and r['protocol']==proto and r['requested_holdout']==ratio];row.append(f'{rr[0]["macro_nrmse"]:.4f}' if rr else '--')
    fullrows.append(row)
  table('coverage_'+domain,['Condition',r'Holdout\%','ORCX','MLI-ext.','Anchor','Sel. GP','Binary','Full'],fullrows,'llrrrrrr')
 fig.legend(*axs[0,0].get_legend_handles_labels(),loc='upper center',ncol=4,frameon=False,fontsize=8);fig.text(.5,.015,'Requested characterization holdout (%)',ha='center')
 save(fig,'coverage_four_ratios')
 return scores,inventory

def physical():
 rows=[]
 with gzip.open(O/'physical_predictions.jsonl.gz','rt') as f:rows=[json.loads(l) for l in f]
 for r in map(json.loads,(R/'results/layout_offgrid_20261115/predictions_fem.jsonl').read_text().splitlines()):
  rows.append(dict(r,components=r['component']))
 # Existing adapted AttentionCap appears in the runtime results, separately below.
 summary=[]
 for method in sorted({r['method'] for r in rows}):
  rr=[r for r in rows if r['method']==method];assert len(rr)==71,(method,len(rr));vals=[];weighted=[]
  for fam in sorted({r['family'] for r in rr}):
   rs=[r for r in rr if r['family']==fam];y=np.array([r['reference'] for r in rs]);p=np.array([r['prediction'] for r in rs]);e=p-y;w=np.array([r['occurrence_count']/r['sampling_probability'] for r in rs])
   den=(y*y).sum(0);keep=den>0;vals.extend(np.sqrt((e*e).sum(0)[keep]/den[keep]));weighted.extend(np.sqrt((w[:,None]*e*e).sum(0)[keep]/(w[:,None]*y*y).sum(0)[keep]))
  err=np.abs(np.array([r['prediction'] for r in rr])-np.array([r['reference'] for r in rr]));summary.append(dict(method=method,queries=71,macro_nrmse=float(np.mean(vals)),HT_macro_nrmse=float(np.mean(weighted)),p95_nonzero_F_per_m=float(np.quantile(err[:,:2],.95)),p99_nonzero_F_per_m=float(np.quantile(err[:,:2],.99))))
 csvwrite(O/'physical_summary.csv',summary);idx={r['method']:r for r in summary}
 table('production_kernels',['Method','NRMSE',r'P95 (pF/m)'],[[LABEL[m],f'{idx[m]["macro_nrmse"]:.5f}',f'{idx[m]["p95_nonzero_F_per_m"]*1e12:.3f}'] for m in ['openrcx_kernel','mli','binary','full','binary_compute','full_compute']],'lrr')
 runtime={r['method']:r for r in csv.DictReader((R/'results/runtime_accuracy_20261115/accuracy_runtime.csv').open()) if r['task']=='fem' and int(r['batch_limit'])==32}
 controls=[('anchor','Anchor'),('cmi','CMI extension'),('gp','Selected GP'),('affine','Local affine'),('residual','Ungated'),('binary','Binary'),('full','Full'),('mlp_adapt','Adapted MLP'),('cnp','CNP'),('attentioncap_adapted','Adapted AC')]
 table('kernel_components',['Control','NRMSE',r'Warm ms/Q'],[[label,f'{float(runtime[m]["macro_nrmse"]):.5f}',f'{float(runtime[m]["amortized_wall_ms"]):.3f}'] for m,label in controls],'lrr')

 return summary

def deployment():
 rs=list(csv.DictReader((O/'native_flow_timing.csv').open()));pre=read(O/'preparation.json');inventory=list(csv.DictReader((O/'inventory_cost.csv').open()));out=[];details=[]
 for case in sorted({r['case'] for r in rs}):
  orig=[r for r in rs if r['case']==case and r['method']=='original'];base=np.mean([float(r['extraction_s']) for r in orig]);baseres=np.mean([float(r['wall_s'])-sum(float(r[k+'_s']) for k in ['layout_and_libs','rule_registration','extraction','spef_write','sta_read','sta_analysis']) for r in orig]);plat=case.split('/')[0]
  for method in ['disabled','pass','binary','full']:
   rr=[r for r in rs if r['case']==case and r['method']==method];extract=np.array([float(r['extraction_s']) for r in rr]);nativeprep=np.mean([float(r['native_build_s'])+float(r['injection_s']) for r in rr]);residual=np.mean([float(r['wall_s'])-sum(float(r[k+'_s']) for k in ['layout_and_libs','rule_registration','extraction','spef_write','sta_read','sta_analysis']) for r in rr]);prep=0.
   if method in ['binary','full','pass']:
    a=next(r for r in pre['rows'] if r['platform']==plat and r['method']==method);prep=a['prediction_wall_s']+a['write_wall_s']+pre['data_load']['wall_s']+next(r for r in pre['platforms'] if r['platform']==plat)['support_mapping']['wall_s']
    # Full per-process cold inventory extraction and a complete shared-model load
    # are charged per independently prepared library; not hidden as free shared work.
    inventory_row=next(r for r in inventory if r['case']==plat+'/aes')
    prep+=float(inventory_row['wall_s'])-sum(float(inventory_row[k+'_s']) for k in ['spef_write','sta_read','sta_analysis'])
    if method!='pass':prep+=pre['model_bundle_load']['wall_s']
   receipts=[read(O/'native'/case/method/str(i)/'receipt.json') for i in range(3)];comp=receipts[0]['comparison']
   row=dict(case=case,method=method,repetitions=3,base_extract_s=float(base),extract_mean_s=float(extract.mean()),extract_sd_s=float(extract.std(ddof=1)),extract_ratio=float(extract.mean()/base),ratio_min=float(min(extract)/base),ratio_max=float(max(extract)/base),native_table_build_and_hook_s=float(nativeprep),prepare_external_cold_s=float(prep),process_residual_s=float(residual),base_process_residual_s=float(baseres),cold_PEX_overhead=float((prep+extract.mean()+residual-base-baseres)/(base+baseres)),warm_PEX_overhead=float((extract.mean()-base)/base),spef_write_s=float(np.mean([float(r['spef_write_s']) for r in rr])),sta_s=float(np.mean([float(r['sta_read_s'])+float(r['sta_analysis_s']) for r in rr])),net_C_nrmse=comp['metrics']['capacitance']['nrmse'],worst_slack_delta_ps=float(rr[0]['worst_slack_ps'])-float(orig[0]['worst_slack_ps']),tns_delta_ps=float(rr[0]['tns_ps'])-float(orig[0]['tns_ps']))
   # compare_spef schema is inspected before final summarization.
   out.append(row)
 csvwrite(O/'deployment_summary.csv',out)
 reuse=[]
 for plat in sorted({r['case'].split('/')[0] for r in out}):
  for method in ['pass','binary','full']:
   rr=[r for r in out if r['case'].split('/')[0]==plat and r['method']==method];assert len(rr)==2
   prep=rr[0]['prepare_external_cold_s'];base_total=sum(r['base_extract_s']+r['base_process_residual_s'] for r in rr);total=prep+sum(r['extract_mean_s']+r['process_residual_s'] for r in rr)
   reuse.append(dict(platform=plat,method=method,designs=2,prepare_once_s=prep,PEX_total_s=total,base_PEX_total_s=base_total,relative_overhead=total/base_total-1,scope='two measured designs, preparation charged once; includes process residual, excludes SPEF/STA; native table build remains per extraction'))
 csvwrite(O/'reuse_cost.csv',reuse)
 table('compute_deployment',['Layout','C err.','Prep.','PEX','SPEF',r'$T/T_0$'],[[r['case'].replace('ihp-sg13g2','IHP').replace('sky130hs','Sky'),f'{r["net_C_nrmse"]:.5f}' if r['net_C_nrmse'] is not None else '--',f'{r["prepare_external_cold_s"]:.2f}',f'{r["extract_mean_s"]:.2f}',f'{r["spef_write_s"]:.2f}',f'{r["extract_ratio"]:.3f}'] for r in out if r['method']=='full'],'lrrrrr')
 stage_rows=[]
 for case in sorted({r['case'] for r in rs}):
  for m in ['original','disabled','pass','binary','full']:
   rr=[r for r in rs if r['case']==case and r['method']==m];v=np.array([float(r['extraction_s']) for r in rr]);d=next((r for r in out if r['case']==case and r['method']==m),None)
   stage_rows.append([case.replace('ihp-sg13g2','IHP').replace('sky130hs','Sky'),m,f'{v.mean():.3f}',f'{v.std(ddof=1):.3f}',f'{np.mean([float(r["spef_write_s"]) for r in rr]):.3f}',f'{np.mean([float(r["sta_read_s"])+float(r["sta_analysis_s"]) for r in rr]):.3f}',f'{d["prepare_external_cold_s"]:.2f}' if d else '0',f'{d["net_C_nrmse"]:.5f}' if d else '0',f'{d["worst_slack_delta_ps"]:+.3f}' if d else '0'])
 table('native_stages',['Layout','Mode','PEX','SD','SPEF','STA','Prep.','C err.',r'$\Delta$slack (ps)'],stage_rows,'llrrrrrrr')

 return out
if __name__=='__main__':
 scores,inv=coverage();phys=physical();dep=deployment();write(O/'SUMMARY.json',dict(physical=phys,deployment=dep,coverage_cells=len(scores),coverage_episodes=len(inv)))
