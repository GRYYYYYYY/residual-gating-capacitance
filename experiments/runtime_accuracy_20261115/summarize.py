"""Join measured time to accuracy by task, method AND batch protocol."""
from common_runtime import *
import collections,math,gzip
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=R/'paper/dac_layout_query_revision';FIG=P/'figures'
def getcsv(path):return list(csv.DictReader(open(path)))
def main():
    raw=[];pred=[];summary=[];metrics=[]
    workload=read(O/'WORKLOADS.json')
    for kind in ['fem','native']:
        rr=getcsv(O/f'timing_{kind}.csv')
        for r in rr:
            r.update(task_id=kind,batch_id=f"{kind}:{r['table_id']}:{r['batch_limit']}:{r['batch_start']}",ensemble_member_count=3 if r['method'] in ['full','binary','residual','mlp_adapt','cnp','attentioncap_adapted'] else 0,independent_contexts=1)
            meta=next(g for g in workload['groups'][kind] if g['table_id']==r['table_id']);r.update(output_components=json.dumps(meta['components']),output_units=json.dumps(meta['units']),S_hash=meta['support_sha256'],input_material_regions=meta['material_regions'])
            union=next(b['union_geometries'] for b in meta['batches'] if b['limit']==int(r['batch_limit']) and b['start']==int(r['batch_start']))
            r['evaluated_geometry_count']=int(r['query_count']) if r['method'] in ['mlp_adapt','attentioncap_adapted'] else union
            if r['method'] in ['full','binary','residual']:r['neural_sequence_length']=union+meta['material_regions'];r['independent_neural_structures']=1
            elif r['method']=='attentioncap_adapted':r['neural_sequence_length']=meta['conductor_count']+1;r['independent_neural_structures']=int(r['query_count'])
            else:r['neural_sequence_length']='not a self-attention sequence';r['independent_neural_structures']='not applicable'
        raw.extend(rr);pred.extend(map(json.loads,(O/f'predictions_{kind}.jsonl').read_text().splitlines()))
    csvwrite(O/'timing_raw.csv',raw)
    for kind,m,b in sorted(set((r['task'],r['method'],r['batch_limit']) for r in pred)):
        rs=[r for r in pred if (r['task'],r['method'],r['batch_limit'])==(kind,m,b)]
        assert len({r['query_id'] for r in rs})==len(rs)==(71 if kind=='fem' else 480)
        tt=[r for r in raw if (r['task'],r['method'],int(r['batch_limit']))==(kind,m,b)]
        totals=[sum(float(r['wall_s']) for r in tt if int(r['block'])==i) for i in range(20)]
        cpus=[sum(float(r['cpu_s']) for r in tt if int(r['block'])==i) for i in range(20)]
        latency=np.array([float(r['wall_s']) for r in tt]);nr=[];wnr=[];ae=[]
        for proc,fam in sorted(set((r['process'],r['family']) for r in rs)):
            sub=[r for r in rs if (r['process'],r['family'])==(proc,fam)]
            y=np.array([r['reference'] for r in sub]);p=np.array([r['prediction'] for r in sub]);w=np.array([r['occurrence_count']/r['sampling_probability'] for r in sub])
            for j,name in enumerate(sub[0]['components']):
                e=p[:,j]-y[:,j];nrmse=float(np.sqrt(np.sum(e*e)/np.sum(y[:,j]**2))) if np.any(y[:,j]) else None
                weighted=float(np.sqrt(np.sum(w*e*e)/np.sum(w*y[:,j]**2))) if np.any(y[:,j]) else None
                metrics.append(dict(task=kind,method=m,batch_limit=b,process=proc,family=fam,component=name,n=len(sub),nrmse=nrmse,occurrence_HT_nrmse=weighted,mae=float(np.mean(abs(e))),signed=float(np.mean(e)),p95_absolute=float(np.quantile(abs(e),.95,method='inverted_cdf')),p99_absolute=float(np.quantile(abs(e),.99,method='inverted_cdf'))))
                metrics[-1]['unit']=sub[0]['unit']
                if nrmse is not None:nr.append(nrmse);wnr.append(weighted);ae.extend(abs(e))
        prep=read(O/f'preparation_{kind}.json');fit=sum(r['wall_s'] for r in prep['contexts'] if r['method']==m)
        row=dict(task=kind,method=m,batch_limit=b,queries=len(rs),macro_nrmse=float(np.mean(nr)),occurrence_HT_macro_nrmse=float(np.mean(wnr)),p95_nonzero_component_absolute=float(np.quantile(ae,.95,method='inverted_cdf')),p99_nonzero_component_absolute=float(np.quantile(ae,.99,method='inverted_cdf')),mean_total_wall_s=float(np.mean(totals)),mean_total_cpu_s=float(np.mean(cpus)),sd_total_wall_s=float(np.std(totals,ddof=1)),amortized_wall_ms=float(np.mean(totals))/len(rs)*1e3,amortized_cpu_ms=float(np.mean(cpus))/len(rs)*1e3,throughput_queries_s=len(rs)/float(np.mean(totals)),batch_mean_ms=float(np.mean(latency))*1e3,batch_median_ms=float(np.median(latency))*1e3,batch_p95_ms=float(np.quantile(latency,.95))*1e3,single_request_p95_ms=float(np.quantile(latency,.95))*1e3 if b==1 else None,fit_once_all_contexts_wall_s=fit,batch_count_per_pass=len(tt)//20,mean_actual_query_batch=len(rs)/(len(tt)/20),reference='independent certified fine FEM, F/m' if kind=='fem' else 'native evaluator agreement; rule units; not physical truth',hardware='Xeon Gold 6530, CPU24, one thread, float32 neural / float64 numerical',load_scope='shared bundle cold load reported separately in preparation JSON; not assigned repeatedly to each method')
        summary.append(row)
        if kind=='native':
            row['p95_nonzero_component_absolute']=None;row['p99_nonzero_component_absolute']=None
            row['absolute_error_scope']='Native absolute errors are reported per process/family/component in component_accuracy.csv; no cross-process physical-unit pooling'
    csvwrite(O/'component_accuracy.csv',metrics);csvwrite(O/'accuracy_runtime.csv',summary)
    eq={kind:read(O/f'equivalence_{kind}.json') for kind in ['fem','native']};eq['attention']=read(O/'attention_equivalence.json');eq['native_cpp']=read(O/'native_kernel_validation.json');eq['rules']=read(O/'rule_preparation.json');eq['solver']=read(O/'solver_task_match.json')
    for name in ['cnp_staged_equivalence','cached_query_equivalence','native_support_equivalence']:
        if (O/(name+'.json')).exists():eq[name]=read(O/(name+'.json'))
    write(O/'OUTPUT_EQUIVALENCE.json',dict(passed=all(x['passed'] for k in ['fem','native'] for x in eq[k]) and eq['attention']['passed'] and eq['native_cpp']['passed'],canonical_source_scaled_tolerance=2e-6,native_scaled_tolerance=1e-12,solver_scaled_tolerance=1e-8,checks=eq))
    # Standalone native comparison; never merged with the FEM physical ranking.
    cpp=getcsv(O/'native_kernel_timing.csv');ffi=getcsv(O/'native_ctypes_timing.csv')
    native_ns=np.array([float(r['wall_s'])/(int(r['query_count'])*int(r['inner_repetitions']))*1e9 for r in cpp]);ffi_ns=np.array([float(r['wall_s'])/int(r['query_count'])*1e9 for r in ffi])
    write(O/'native_kernel_summary.json',dict(mean_ns=float(np.mean(native_ns)),median_ns=float(np.median(native_ns)),p95_block_amortized_ns=float(np.quantile(native_ns,.95)),ctypes_mean_ns=float(np.mean(ffi_ns)),scope='resolved width/context finite getComputeRC counterpart; block amortization, not measured single-request P95; excludes upstream geometry discovery'))
    cr=list(map(json.loads,(O/'native_cpp_predictions.jsonl').read_text().splitlines()));errors=[];absolute=[]
    for proc,fam in sorted(set((r['process'],r['family']) for r in cr)):
        sub=[r for r in cr if (r['process'],r['family'])==(proc,fam)];y=np.array([r['reference'] for r in sub]);p=np.array([r['prediction'] for r in sub]);e=p-y
        for j in range(y.shape[1]):
            if np.any(y[:,j]):errors.append(float(np.sqrt(np.sum(e[:,j]**2)/np.sum(y[:,j]**2))));absolute.extend(abs(e[:,j]))
    summary.append(dict(task='native',method='native_cpp_validated',batch_limit=480,queries=480,macro_nrmse=float(np.mean(errors)),p95_nonzero_component_absolute=float(np.quantile(absolute,.95,method='inverted_cdf')),p99_nonzero_component_absolute=float(np.quantile(absolute,.99,method='inverted_cdf')),amortized_wall_ms=float(np.mean(native_ns))/1e6,amortized_cpu_ms=float(np.mean([float(r['cpu_s'])/(int(r['inner_repetitions'])*int(r['query_count']))*1000 for r in cpp])),throughput_queries_s=1e9/float(np.mean(native_ns)),reference='same 480 native returns, not physical truth',hardware='Xeon Gold 6530 CPU24, C++ double, -O3',timing_scope='loop amortization after width/context resolution; batch latency and single-request P95 NOT measured'))
    summary[-1].update(p95_nonzero_component_absolute=None,p99_nonzero_component_absolute=None,absolute_error_scope='Native source-rule units; no cross-process absolute pooling')
    csvwrite(O/'accuracy_runtime.csv',summary)
    # Native-flow fidelity and overhead, preserving the actual eight design cases.
    flow=getcsv(O/'native_flow_timing.csv');fr=[]
    for case in sorted(set(r['case'] for r in flow)):
        original=[r for r in flow if r['case']==case and r['method']=='original'];base={k:np.mean([float(r[k]) for r in original]) for k in ['extraction_s','wall_s','spef_write_s']}
        for m in ['original','cmi','binary','full']:
            sub=[r for r in flow if r['case']==case and r['method']==m];assert len(sub)==3
            receipt=read(O/'native'/case/m/'0/receipt.json');comp=receipt['comparison']['metrics']['capacitance']
            keys=['wall_s','cpu_s','extraction_s','spef_write_s','sta_read_s','sta_analysis_s','rule_registration_s','peak_rss_kib']
            data={f'mean_{k}':float(np.mean([float(r[k]) for r in sub])) for k in keys}
            fr.append(dict(case=case,method=m,**data,extraction_ratio=data['mean_extraction_s']/base['extraction_s'],process_wall_ratio=data['mean_wall_s']/base['wall_s'],sd_extraction_s=float(np.std([float(r['extraction_s']) for r in sub],ddof=1)),rule_bytes=int(sub[0]['rule_bytes']),worst_slack=float(sub[0]['worst_slack']),tns=float(sub[0]['tns']),slack_delta_vs_original=float(sub[0]['worst_slack'])-float(original[0]['worst_slack']),tns_delta_vs_original=float(sub[0]['tns'])-float(original[0]['tns']),capacitance_metrics=json.dumps(comp,sort_keys=True)))
            fr[-1].update(sta_time_unit=sub[0]['sta_time_unit'],worst_slack_ps=float(sub[0]['worst_slack_ps']),tns_ps=float(sub[0]['tns_ps']),slack_delta_ps=float(sub[0]['worst_slack_ps'])-float(original[0]['worst_slack_ps']),tns_delta_ps=float(sub[0]['tns_ps'])-float(original[0]['tns_ps']),capacitance_units=json.dumps(receipt['comparison']['units']['*C_UNIT']))
    csvwrite(O/'native_flow_summary.csv',fr)
    preparation=read(O/'rule_preparation.json');pr=[]
    for m in ['cmi','binary','full']:
        entries=[r for r in preparation['rows'] if r['method']==m]
        pr.append(dict(method=m,shared_data_load_s=preparation['data_load']['wall_s'],shared_model_bundle_load_s=preparation['shared_model_bundle_load']['wall_s'],shared_support_selection_s=preparation['support_selection']['wall_s'],prediction_all_four_platforms_s=entries[0]['prediction_all_platforms']['wall_s'],payload_write_s=entries[0]['payload_write']['wall_s'],export_all_four_platforms_s=sum(e['export']['wall_s'] for e in entries),actual_designs=8,actual_designs_per_platform=2))
    csvwrite(O/'rule_preparation_summary.csv',pr)
    shared=sum(preparation[k]['wall_s'] for k in ['data_load','shared_model_bundle_load','support_selection']);deployment=[]
    for r in pr:
        m=r['method'];sub=[f for f in fr if f['method']==m];predict_export=r['prediction_all_four_platforms_s']+r['payload_write_s']+r['export_all_four_platforms_s']
        extraction_output=sum(f['mean_extraction_s']+f['mean_spef_write_s'] for f in sub)
        deployment.append(dict(method=m,actual_designs=8,actual_process_libraries=4,designs_per_library=2,one_off_predict_export_s=predict_export,sum_mean_extract_plus_spef_s=extraction_output,marginal_total_after_shared_setup_s=predict_export+extraction_output,marginal_total_including_native_process_start_layout_and_STA_s=predict_export+sum(f['mean_wall_s'] for f in sub),mean_STA_read_and_analysis_s=sum(f['mean_sta_read_s']+f['mean_sta_analysis_s'] for f in sub)))
    write(O/'deployment_cost.json',dict(shared_comparison_setup_once_s=shared,shared_bundle_loading_scope=preparation['scope'],rows=deployment,note='Observed D=8 comparison pipeline, two designs per process library. Shared setup is counted once across methods. Marginal values are not isolated cold standalone deployments; fresh-process load costs are separately measured. No per-query amortization using unmeasured native call counts, no online Amdahl estimate.'))
    plot(summary,fr,pr,native_ns)
    budget=sum(read(O/f'completed_{k}.json')['cpu_s'] for k in ['fem','native'])+read(O/'solver_task_match.json')['worker_cost']['cpu_s']+read(O/'native_flow_completed.json')['total_cpu_s']+preparation['total']['cpu_s']+read(O/'attention_equivalence.json')['cpu_s']
    if (O/'cached_query_equivalence.json').exists():budget+=read(O/'cached_query_equivalence.json')['cpu_s']
    if (O/'cnp_staged_equivalence.json').exists():budget+=sum(r['cpu_s'] for r in read(O/'cnp_staged_equivalence.json'))
    if (O/'cold_load.json').exists():budget+=sum(r['total']['cpu_s'] for r in read(O/'cold_load.json')['rows'])
    tables(summary)
    write(O/'SUMMARY.json',dict(queries={'fem':71,'native':480},repetitions=20,warmups=3,batches=[1,8,32],solver_repetitions=3,native_runs=len(flow),accounted_main_cpu_core_hours=budget/3600,accounting='Main completed experiment CPU; launch/import, failed setup checks, compilation and analysis additionally accounted in resource ledger. Not a hard upper-bound claim.',runtime_scope='Query replay and same-node offline export; no online replacement or added rule nodes',source_training='No new source training; frozen source training receipts retained under results/dac_characterization_20261114; shared characterization S not charged per Q'))
    print(json.dumps({'fem32':[r for r in summary if r['task']=='fem' and r['batch_limit']==32],'native_kernel_ns':float(np.mean(native_ns)),'main_cpu_core_hours':budget/3600},indent=2))
def tables(summary):
    lookup={(r['task'],r['method'],r['batch_limit']):r for r in summary}
    methods=[('cmi','Multilinear'),('anchor','Support anchor'),('affine','Local affine'),('gp','RBF-GP'),('residual','Ungated'),('binary','Binary'),('full','Full'),('mlp_adapt','Adapted MLP'),('cnp','CNP'),('attentioncap_adapted','Adapted AC')]
    lines=[r'\begin{tabular}{lrrrr}\toprule',r'Method & Native & FEM & FEM$_w$ & ms/Q\\\midrule']
    detail=[r'\begin{tabular}{lrrrrr}\toprule',r'Method & NRMSE & ms/Q & Q=1 mean & Q=1 P95 & Fit (s)\\\midrule']
    for m,name in methods:
        f=lookup['fem',m,32];single=lookup['fem',m,1];n=lookup.get(('native',m,32));native=f'{n["macro_nrmse"]:.5f}' if n else '--'
        lines.append(f'{name} & {native} & {f["macro_nrmse"]:.5f} & {f["occurrence_HT_macro_nrmse"]:.5f} & {f["amortized_wall_ms"]:.3f}'+r'\\')
        detail.append(f'{name} & {f["macro_nrmse"]:.5f} & {f["amortized_wall_ms"]:.3f} & {single["batch_mean_ms"]:.3f} & {single["single_request_p95_ms"]:.3f} & {f["fit_once_all_contexts_wall_s"]:.2f}'+r'\\')
    lines.append(r'\bottomrule\end{tabular}');detail.append(r'\bottomrule\end{tabular}')
    (P/'tables/offgrid_runtime.tex').write_text('\n'.join(lines)+'\n');(P/'tables/runtime_detail.tex').write_text('\n'.join(detail)+'\n')
def plot(summary,flow,prep,native_ns):
    methods=['anchor','cmi','affine','gp','residual','binary','full','mlp_adapt','cnp','attentioncap_adapted']
    names=dict(anchor='Anchor',cmi='CMI',affine='Affine',gp='GP',residual='Residual',binary='Binary',full='Full',mlp_adapt='Adapted MLP',cnp='CNP',attentioncap_adapted='Adapted AttentionCap')
    colors=dict(zip(methods,plt.get_cmap('tab10').colors));plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'ps.fonttype':42})
    fig,ax=plt.subplots(1,3,figsize=(10.3,2.75),gridspec_kw={'width_ratios':[1.45,1,1]},layout='constrained')
    for m in methods:
        rr=sorted([r for r in summary if r['task']=='fem' and r['method']==m],key=lambda r:r['batch_limit'],reverse=True)
        ax[0].plot([r['amortized_wall_ms'] for r in rr],[r['macro_nrmse'] for r in rr],'-',lw=.6,c=colors[m],alpha=.5)
        for r in rr:ax[0].scatter(r['amortized_wall_ms'],r['macro_nrmse'],s=24 if r['batch_limit']==32 else 13,marker={32:'o',8:'s',1:'^'}[r['batch_limit']],c=[colors[m]],label=names[m] if r['batch_limit']==32 else None)
    solver=read(O/'solver_task_match.json');ax[0].scatter(solver['resident_mean_total_wall_s']/71*1000,0,c='black',marker='*',s=38,label='1-RHS fine FEM')
    ax[0].set_xscale('log');ax[0].set_yscale('symlog',linthresh=.001);ax[0].set_ylim(-.00008,1.2);ax[0].set_yticks([0,.001,.01,.1,1],['0','.001','.01','.1','1']);ax[0].set_xlabel('Warm wall ms / actual query');ax[0].set_ylabel('Macro NRMSE (71 FEM queries)');ax[0].set_title('(a) Same S and physical outputs')
    handles,labels=ax[0].get_legend_handles_labels();fig.legend(handles,labels,fontsize=8,ncol=6,loc='lower center',bbox_to_anchor=(.5,-.12),frameon=False)
    for i,m in enumerate(['cmi','binary','full']):
        rr=[r for r in flow if r['method']==m];v=[r['extraction_ratio'] for r in rr]
        ax[1].scatter([i+(j-3.5)*.045 for j in range(8)],v,s=15,c=[colors[m]]);ax[1].plot([i-.23,i+.23],[np.median(v)]*2,c='black',lw=1)
    ax[1].axhline(1,c='gray',ls='--',lw=.6);ax[1].set_xticks(range(3),['CMI','Binary','Full']);ax[1].set_ylabel('Extraction / original (3-run mean)');ax[1].set_title('(b) Eight fixed layouts, B=8')
    base=np.array([r['prediction_all_four_platforms_s'] for r in prep]);export=np.array([r['export_all_four_platforms_s']+r['payload_write_s'] for r in prep]);ax[2].bar(range(3),base,label='Predict',color='#467daa');ax[2].bar(range(3),export,bottom=base,label='Export',color='#e7ad51')
    ax[2].set_xticks(range(3),['CMI','Binary','Full']);ax[2].set_ylabel('One-off wall seconds (4 rule files)');ax[2].set_title('(c) Fixed-node preparation');ax[2].legend(fontsize=7)
    for ext in ['pdf','png']:fig.savefig(FIG/f'runtime_accuracy.{ext}',dpi=200,bbox_inches='tight')
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,3.4),layout='constrained')
    for m in methods[:-1]:
        rr=sorted([r for r in summary if r['task']=='native' and r['method']==m],key=lambda r:r['batch_limit'],reverse=True)
        ax.plot([r['amortized_wall_ms'] for r in rr],[r['macro_nrmse'] for r in rr],'.-',label=names[m],color=colors[m],lw=.8)
    ax.scatter(np.mean(native_ns)/1e6,0,marker='*',c='black',label='Validated C++ getter counterpart')
    ax.set_xscale('log');ax.set_xlabel('Warm wall ms / geometry query');ax.set_ylabel('Macro NRMSE vs Native (480 queries)');ax.legend(fontsize=7,ncol=2);ax.set_title('Native agreement only; not an electrostatic accuracy ranking')
    for ext in ['pdf','png']:fig.savefig(FIG/f'runtime_native_agreement.{ext}',dpi=200)
    plt.close(fig)
if __name__=='__main__':main()
