"""Rebuild aggregate tables and figures solely from immutable result records."""
import csv,gzip,json,collections,itertools
from common import *
from pdkcap.metrics import summarize
R=ROOT/'results/dac_characterization_20261114'
OUT=R/'summary'
def csvwrite(name,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def read(p):return [json.loads(l) for l in gzip.open(p,'rt')]
def table_error(r):
    sy=np.asarray(r['squared_truth']);se=np.asarray(r['squared_error']);take=sy>0
    return float(np.sqrt(se[take]/sy[take]).mean()) if take.any() else None

def bootstrap(rs,method,other):
    # Dependence groups cross families for FEM; resample groups within process,
    # preserving all families and data-seed replicates together.
    a=[r for r in rs if r['method']==method];b=[r for r in rs if r['method']==other]
    key=lambda r:(r['table_id'],r['data_seed'])
    assert {key(r) for r in a}=={key(r) for r in b}
    cells=sorted({(r['process_id'],r['family'],k) for r in a for k in range(len(r['squared_truth']))})
    groups=sorted({(r['process_id'],r.get('dependency_group',r.get('split_group',r['table_id']))) for r in a});gi={g:i for i,g in enumerate(groups)};ci={c:i for i,c in enumerate(cells)}
    aa=np.zeros((len(groups),len(cells)));bb=aa.copy();yy=aa.copy()
    identity={r['table_id']:(r['process_id'],r.get('dependency_group',r.get('split_group',r['table_id']))) for r in a}
    for dest,rr in [(aa,a),(bb,b)]:
        for r in rr:
            g=gi[identity[r['table_id']]];proc=r['process_id'];fam=r['family']
            for j,v in enumerate(r['squared_error']):dest[g,ci[proc,fam,j]]+=v
            if dest is aa:
                for j,v in enumerate(r['squared_truth']):yy[g,ci[proc,fam,j]]+=v
    rng=np.random.default_rng(20261114);weights=np.zeros((2000,len(groups)))
    for proc in sorted({g[0] for g in groups}):
        ids=[i for i,g in enumerate(groups) if g[0]==proc];weights[:,ids]=rng.multinomial(len(ids),np.ones(len(ids))/len(ids),size=2000)
    sy=weights@yy;valid=sy>0
    d=np.divide(weights@aa,sy,out=np.zeros_like(sy),where=valid)**.5-np.divide(weights@bb,sy,out=np.zeros_like(sy),where=valid)**.5
    scores=d.sum(1)/np.maximum(valid.sum(1),1)
    point=summarize(a)['nrmse']-summarize(b)['nrmse']
    return dict(method=method,comparator=other,delta_nrmse=point,ci_low=float(np.quantile(scores,.025)),ci_high=float(np.quantile(scores,.975)),dependency_groups=len(groups),replicates=2000,statistical_scope='paired process-stratified dependency-group; data seeds inside group; pointwise')

def main():
    OUT.mkdir(exist_ok=True);rows=[];run=[]
    for s in MODELS:
        p=R/f'confirmation_{s}';receipt=json.loads((p/'COMPLETED.json').read_text());assert receipt['failed']==0
        rs=read(p/'records.jsonl.gz');rows+=rs;run.append(dict(setting=s,**receipt))
    for s in ('reference','to_asap7'):
        p=R/f'attention/{s}_confirmation/records.jsonl.gz'
        if p.exists() and (p.parent/'COMPLETED.json').exists():rows+=read(p)
    csvwrite('run_completion.csv',run)
    grouped=collections.defaultdict(list)
    for r in rows:
        if r['status']=='ok':grouped[r['setting'],r['strategy'],r['method'],r['budget']].append(r)
    curves=[];components=[];cost=[];attainment=[]
    for (s,strategy,m,b),rs in sorted(grouped.items()):
        sm=summarize(rs);ys={r['table_id'] for r in rs};p=dict(setting=s,strategy=strategy,method=m,budget=b,tables=len(ys),data_seeds=len({r['data_seed'] for r in rs}),nrmse=sm['nrmse'],failed=0,mean_completion_wall_seconds=float(np.mean([r['prediction_and_adaptation_wall_seconds'] for r in rs])))
        curves.append(p)
        for cell in sm['cells']+sm['zero_truth_groups']:components.append(dict(setting=s,strategy=strategy,method=m,budget=b,**cell))
    for r in rows:
        zero=r['method'] in ('mlp_zero','attentioncap_zero')
        cost.append(dict(setting=r['setting'],method=r['method'],strategy=r['strategy'],table_id=r['table_id'],data_seed=r['data_seed'],evaluation_support_budget=r['budget'],unique_reference_queries=0 if zero else r['budget'],solver_cpu_seconds_fine=0 if zero else r.get('solver_cpu_seconds_fine'),solver_cpu_seconds_validated=0 if zero else r.get('solver_cpu_seconds_validated'),prediction_and_adaptation_wall_seconds=r['prediction_and_adaptation_wall_seconds'],prediction_and_adaptation_cpu_seconds=r.get('prediction_and_adaptation_cpu_seconds'),selection_wall_seconds=0 if zero else r.get('selection_wall_seconds'),solver_cost_kind='none: source-only Q prediction' if zero else r.get('solver_cost_kind','recorded-cost replay'),source_generation_cost='historical; see geometry index, not allocated here',source_training_cost='see training_cost.csv',new_solver_wall_seconds=None))
    trajectories=collections.defaultdict(list)
    for r in rows:
        if r['strategy']=='farthest' and r['method'] not in ('mlp_zero','attentioncap_zero'):trajectories[r['setting'],r['method'],r['table_id'],r['data_seed']].append(r)
    for (s,m,tid,seed),rs in trajectories.items():
        thresholds=json.loads((HERE/f'selected_{s}.json').read_text())['thresholds']
        for qi,tau in enumerate(thresholds):
            attained=sorted([r for r in rs if table_error(r) is not None and table_error(r)<=tau],key=lambda r:r['budget'])
            best=attained[0] if attained else None
            attainment.append(dict(setting=s,method=m,table_id=tid,data_seed=seed,threshold_index=qi,threshold=tau,attained=best is not None,min_measured_budget=None if best is None else best['budget'],fine_cpu_seconds=None if best is None else best.get('solver_cpu_seconds_fine'),validated_cpu_seconds=None if best is None else best.get('solver_cpu_seconds_validated'),max_measured_budget=max(r['budget'] for r in rs),zero_truth=all(table_error(r) is None for r in rs)))
    csvwrite('budget_curves.csv',curves);csvwrite('component_metrics.csv',components);csvwrite('cost_ledger.csv',cost);csvwrite('threshold_attainment.csv',attainment)
    target_cost=[]
    for (setting,strategy,method,budget),rs in sorted(grouped.items()):
        if strategy!='farthest' or method not in ('full','mlp_adapt','binary','anchor'):continue
        fine=[r.get('solver_cpu_seconds_fine') for r in rs];validated=[r.get('solver_cpu_seconds_validated') for r in rs]
        target_cost.append(dict(setting=setting,method=method,budget=budget,mean_recorded_fine_cpu_seconds=float(np.mean(fine)) if all(v is not None for v in fine) else None,mean_recorded_validated_cpu_seconds=float(np.mean(validated)) if all(v is not None for v in validated) else None,mean_completion_adaptation_wall_seconds=float(np.mean([r['prediction_and_adaptation_wall_seconds'] for r in rs])),scope='same S at given B; original CPU and new wall times not added'))
    csvwrite('target_cost_curve.csv',target_cost)
    # Per-table tails retained, no filtering of weak/zero components.
    csvwrite('component_tails.csv',[dict(setting=r['setting'],method=r['method'],budget=r['budget'],strategy=r['strategy'],table_id=r['table_id'],data_seed=r['data_seed'],component=j,units=r['unit'],p95_absolute=v,p99_absolute=(r.get('p99_absolute') or [None]*len(r['p95_absolute']))[j]) for r in rows for j,v in enumerate(r['p95_absolute'])])
    ag=collections.defaultdict(list)
    for r in attainment:ag[r['setting'],r['method'],r['threshold_index']].append(r)
    totals=[]
    for (s,m,qi),rs in ag.items():
        eligible=[r for r in rs if not r['zero_truth']];got=[r for r in eligible if r['attained']]
        totals.append(dict(setting=s,method=m,threshold_index=qi,threshold=rs[0]['threshold'],trajectories=len(eligible),reached=len(got),not_reached=len(eligible)-len(got),zero_truth_trajectories=len(rs)-len(eligible),median_budget_conditional_on_attainment=float(np.median([r['min_measured_budget'] for r in got])) if got else None))
    csvwrite('threshold_summary.csv',totals)
    cis=[]
    for s in MODELS:
        for b in sorted({r['budget'] for r in rows if r['setting']==s}):
            rs=[r for r in rows if r['setting']==s and r['budget']==b and r['strategy']=='farthest'];methods={r['method'] for r in rs}
            for m in ('anchor','affine','gp','residual','binary','mlp_adapt','cnp','attentioncap_adapted'):
                if m in methods:cis.append(dict(setting=s,budget=b,**bootstrap(rs,'full',m)))
    csvwrite('paired_bootstrap.csv',cis)
    # Pair minimum measured budgets on identical table/seed. Censored cases stay.
    paired=[]
    for s in MODELS:
        for qi in range(3):
            lookup={(r['method'],r['table_id'],r['data_seed']):r for r in attainment if r['setting']==s and r['threshold_index']==qi and not r['zero_truth']}
            keys=[k[1:] for k in lookup if k[0]=='full']
            for m in ('anchor','affine','gp','binary','residual','mlp_adapt','cnp','attentioncap_adapted'):
                counters=collections.Counter();ratios=[];cost_pairs=[]
                for k in keys:
                    if (m,*k) not in lookup:continue
                    a,b=lookup[('full',)+k],lookup[(m,)+k]
                    if a['attained'] and b['attained']:
                        av,bv=a['min_measured_budget'],b['min_measured_budget'];counters['both_reached']+=1;counters['full_fewer' if av<bv else 'full_more' if av>bv else 'equal']+=1;ratios.append(av/bv)
                        if a['fine_cpu_seconds'] is not None and b['fine_cpu_seconds'] is not None:cost_pairs.append((a['fine_cpu_seconds'],b['fine_cpu_seconds']))
                    else:counters['full_only' if a['attained'] else 'comparator_only' if b['attained'] else 'neither']+=1
                if counters:paired.append(dict(setting=s,threshold_index=qi,comparator=m,**counters,median_full_to_comparator_budget_ratio_both_reached=float(np.median(ratios)) if ratios else None,sum_full_fine_cpu_seconds_both_reached=sum(a for a,b in cost_pairs) if cost_pairs else None,sum_comparator_fine_cpu_seconds_both_reached=sum(b for a,b in cost_pairs) if cost_pairs else None,median_full_to_comparator_fine_cpu_ratio_both_reached=float(np.median([a/b for a,b in cost_pairs])) if cost_pairs else None))
    csvwrite('paired_attainment.csv',paired)
    training=[]
    for p in sorted(R.glob('learning/*/COMPLETED.json'))+sorted(R.glob('attention/*/COMPLETED.json')):
        d=json.loads(p.read_text())
        if not (p.parent/'checkpoint.pt').exists():continue
        training.append(dict(run=str(p.parent.relative_to(ROOT)),steps=d.get('steps'),cpu_seconds=d.get('cpu_seconds'),wall_seconds=d.get('wall_seconds'),kind='new source training',gpu_seconds=0))
    for r in json.loads((HERE/'MANIFEST.json').read_text())['controls']:training.append(dict(run=r['path'],steps=r['steps'],cpu_seconds=None,wall_seconds=r['historical_wall_seconds'],kind='historical control training',gpu_seconds=None))
    for p in sorted((R/'reverse_transfer').glob('mlp_*.json')):
        d=json.loads(p.read_text());training.append(dict(run=str(p.relative_to(ROOT)),steps=3000,cpu_seconds=None,wall_seconds=d['wall_seconds'],kind='new reverse source training; CPU not separately measured',gpu_seconds=0))
    failed=R/'confirmation_public_failed_fork/FAILED.json'
    if failed.exists():
        d=json.loads(failed.read_text());training.append(dict(run=str(failed.relative_to(ROOT)),steps=None,cpu_seconds=d['worker_cpu_seconds'],wall_seconds=None,kind='invalid execution retained cost',gpu_seconds=0))
    seen=set()
    for setting in MODELS:
        for seed in (0,1,2):
            config=source_config(setting,seed)
            paths=[(ROOT/MODELS[setting]['checkpoints'][seed]['path']).parent/'COMPLETED.json',(ROOT/config['init_from']).parent/'COMPLETED.json']
            for p in paths:
                if str(p) in seen:continue
                seen.add(str(p))
                if p.exists():
                    d=json.loads(p.read_text());training.append(dict(run=str(p),steps=d.get('steps'),cpu_seconds=d.get('cpu_seconds'),wall_seconds=d.get('wall_seconds'),kind='historical full/warm-start training; missing fields unknown',gpu_seconds=None))
    csvwrite('training_cost.csv',training)
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    styles={'full':('Full','#007c91'),'binary':('Binary','#6a4c93'),'residual':('Residual','#c17d11'),'anchor':('Anchor','#666666'),'affine':('Local affine','#218739'),'gp':('GP','#b34b3c'),'mlp_adapt':('Adapted MLP','#cc3377'),'cnp':('CNP','#808000'),'attentioncap_adapted':('Adapted AttentionCap','#44aadd')}
    fig,axs=plt.subplots(1,3,figsize=(12,3.4),layout='constrained')
    for ax,s in zip(axs,MODELS):
        for m,(label,color) in styles.items():
            ds=sorted([r for r in curves if r['setting']==s and r['method']==m and r['strategy']=='farthest'],key=lambda x:x['budget'])
            if ds:ax.plot([r['budget'] for r in ds],[r['nrmse'] for r in ds],'o-',label=label,color=color,markersize=3)
        ax.set(title=s,xlabel='Unique observed geometries',ylabel='Macro NRMSE',xscale='log',yscale='log');ax.grid(alpha=.2)
        ticks=sorted({r['budget'] for r in curves if r['setting']==s and r['strategy']=='farthest'});ax.set_xticks(ticks,[str(b) for b in ticks]);ax.xaxis.set_minor_formatter(plt.NullFormatter())
    handles,labels=axs[-1].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=5,fontsize=8)
    fig.savefig(OUT/'budget_accuracy.pdf');fig.savefig(OUT/'budget_accuracy.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(12,3.3),layout='constrained')
    for ax,s in zip(axs,MODELS):
        ds=[r for r in totals if r['setting']==s and r['threshold_index']==1 and r['method'] in styles];ax.bar(range(len(ds)),[r['reached']/r['trajectories'] for r in ds],color=[styles[r['method']][1] for r in ds]);ax.set_xticks(range(len(ds)),[styles[r['method']][0] for r in ds],rotation=55,ha='right',fontsize=7);ax.set(title=s,ylabel='Fraction reaching validation-defined error',ylim=(0,1))
    fig.savefig(OUT/'threshold_coverage.pdf');fig.savefig(OUT/'threshold_coverage.png',dpi=180);plt.close(fig)
    print('summaries',len(rows),len(curves),len(cis),flush=True)
if __name__=='__main__':main()
