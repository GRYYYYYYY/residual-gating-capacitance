"""Reconstruct the unchanged Fig.4 statistic and cluster-paired uncertainty."""
from pathlib import Path
import collections,csv,gzip,hashlib,json
import numpy as np
R=Path(__file__).resolve().parents[2]
O=R/'results/dac_main13_integrated_revision/main13_20261117';O.mkdir(parents=True,exist_ok=True)
P=R/'paper/dac_layout_query_revision';D=R/'docs/dac_main13_integrated_revision'
M=['openrcx_kernel','mli_sparse','residual','binary','full','anchor','numerical_only']
CONDS=[('inside','mcar'),('inside','block'),('outside','mcar'),('outside','block'),('outside','extrapolation')]
SEEDS=[11,29,47,71,101]
def write(name,rows):
 with (O/name).open('w') as f:
  w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def score(a):
 # [...,seed,stratum,method,{SSE,SST}]; group/component first, then seed.
 e,y=a[...,0],a[...,1]
 with np.errstate(invalid='ignore',divide='ignore'):v=np.where(y>0,np.sqrt(e/y),np.nan)
 return np.nanmean(np.nanmean(v,axis=-2),axis=-2)
def main():
 cells=[];paired=[];checks={};sources={};inventory=[]
 plotted={(r['domain'],r['regime'],r['protocol'],float(r['requested_holdout']),r['method']):float(r['macro_nrmse']) for r in csv.DictReader((P/'tables/coverage_with_ungated.csv').open())}
 cfg=json.loads((R/'configs/paper_models.json').read_text())
 for domain in cfg:
  inv=list(csv.DictReader((R/f'results/pex_kernel_revision/coverage_inventory_{domain}.csv').open()));inventory+=inv
  valid={r['SQ_hash'] for r in inv if r['openrcx_applicable']=='True'}
  tables={t['table_id']:t for t in map(json.loads,(R/cfg[domain]['cohort']).read_text().splitlines())}
  def group(t):return f"{t['process_id']}-layer{t['metal']}" if t['domain']=='ctf_derived_2d' else t.get('split_group',t['table_id'])
  records=[]
  for path in [R/f'results/pex_kernel_revision/coverage_{domain}.jsonl.gz',P/f'trials/fig4_ungated_20261116T230943/ungated_{domain}.jsonl.gz']:
   sources[str(path.relative_to(R))]=sha(path)
   with gzip.open(path,'rt') as f:
    records.extend(r for r in map(json.loads,f) if r['SQ_hash'] in valid and r['method'] in M and r['segment'] not in ['all','complete_cell'])
  maxdiff=0.
  for reg,proto in CONDS:
   for ratio in [.1,.3,.5,.7]:
    rr=[r for r in records if r['protocol']==proto and r['ratio']==ratio and ('outside' if r['segment']=='outside' else 'inside')==reg]
    groups=sorted({group(tables[r['table_id']]) for r in rr});strata=sorted({(r['process_id'],r['family'],k) for r in rr for k in range(len(r['squared_error']))})
    gi={g:i for i,g in enumerate(groups)};si={s:i for i,s in enumerate(strata)}
    a=np.zeros((len(groups),5,len(strata),len(M),2));identities=collections.defaultdict(dict)
    for r in rr:
     key=(r['table_id'],r['mask_seed'],r['segment']);identity=(r['scored_indices'],r['squared_truth'])
     identities[key][r['method']]=identity
     for k,(e,y) in enumerate(zip(r['squared_error'],r['squared_truth'])):
      a[gi[group(tables[r['table_id']])],SEEDS.index(r['mask_seed']),si[(r['process_id'],r['family'],k)],M.index(r['method'])]+=[e,y]
    assert all(len(x)==len(M) and all(v==x['full'] for v in x.values()) for x in identities.values())
    point=score(a.sum(0));rng=np.random.default_rng(20261117)
    # Stratified by process: retain process/family macro weighting and correlated masks.
    weights=np.zeros((1000,len(groups)))
    for process in sorted({r['process_id'] for r in rr}):
     ids=sorted({gi[group(tables[r['table_id']])] for r in rr if r['process_id']==process})
     weights[:,ids]=rng.multinomial(len(ids),np.ones(len(ids))/len(ids),1000)
    boot=score(np.einsum('bg,gscmk->bscmk',weights,a,optimize=True));base=min(point[:2]);bb=boot[:,:2].min(1)
    meta=dict(domain=domain,regime=reg,protocol=proto,requested_holdout=ratio,independent_groups=len(groups),tables=len({r['table_id'] for r in rr}))
    for mi,m in enumerate(M):
     if m in M[:5]:maxdiff=max(maxdiff,abs(point[mi]-plotted[(domain,reg,proto,ratio,m)]))
     lo,hi=np.quantile(boot[:,mi]-bb,[.025,.975]);rat=point[mi]/base if base>0 else (float('inf') if point[mi]>0 else float('nan'))
     cells.append(dict(**meta,method=m,macro_nrmse=point[mi],openrcx=point[0],mli_ext=point[1],stronger_baseline=base,error_ratio=rat,improvement_margin=1-rat,absolute_gap_to_stronger=point[mi]-base,paired_gap_ci_low=lo,paired_gap_ci_high=hi,uncertainty='descriptive_cluster_bootstrap_1000;few_groups' if len(groups)<10 else 'cluster_bootstrap_1000'))
    for m in ['openrcx_kernel','mli_sparse','binary','residual','anchor','numerical_only']:
     i=M.index(m);lo,hi=np.quantile(boot[:,4]-boot[:,i],[.025,.975])
     paired.append(dict(**meta,comparison='full-minus-'+m,difference=point[4]-point[i],ci_low=lo,ci_high=hi))
  assert maxdiff<1e-14,(domain,maxdiff)
  checks[domain]={'max_abs_reaggregation_difference':maxdiff,'records':len(records),'episodes':len(inv),'duplicate_rounded_SQ':sum(r['duplicate_of']!='null' for r in inv),'distinct_SQ':len({r['SQ_hash'] for r in inv}),'complete_cell_queries':sum(int(r['complete_cell_queries']) for r in inv),'all_queries':sum(int(r['query_count']) for r in inv)}
 # float32 predictor precision, eight ulps relative to the error scale; no significance interpretation.
 tol=8*np.finfo(np.float32).eps
 summary=[]
 for m in ['residual','binary','full','anchor','numerical_only']:
  rs=[r for r in cells if r['method']==m]
  for policy in ['strict','float32_8eps_relative']:
   def cmp(x,y):
    t=0 if policy=='strict' else tol*max(abs(x),abs(y))
    return -1 if x<y-t else 1 if x>y+t else 0
   row=dict(method=m,policy=policy,conditions=len(rs))
   for b in ['openrcx','mli_ext']:
    cs=[cmp(r['macro_nrmse'],r[b]) for r in rs]
    row.update({b+'_wins':cs.count(-1),b+'_ties':cs.count(0),b+'_losses':cs.count(1)})
   row.update(beats_both=sum(cmp(r['macro_nrmse'],r['stronger_baseline'])==-1 for r in rs),worst_error_ratio=max(r['error_ratio'] for r in rs),minimum_improvement_margin=min(r['improvement_margin'] for r in rs))
   summary.append(row)
 write('coverage_cell_metrics.csv',cells);write('baseline_dominance_summary.csv',summary);write('paired_comparisons.csv',paired)
 margins=sorted([r for r in cells if r['method'] in ['residual','binary','full']],key=lambda r:(r['method'],-r['error_ratio']))
 write('baseline_regression_cases.csv',[r for r in margins if r['error_ratio']>=1]);write('baseline_margin_summary.csv',[r for m in ['residual','binary','full'] for r in [x for x in margins if x['method']==m][:5]])
 (O/'coverage_checks.json').write_text(json.dumps(dict(checks=checks,sources=sources,tolerance_relative=tol,bootstrap_unit='public split_group; FEM/transfer process-layer, stratified by process',bootstrap_seed=20261117,bootstrap_repetitions=1000),indent=2))
 labels={'residual':'Ungated','binary':'Binary','full':'Full','anchor':'Anchor','numerical_only':'Selected GP'}
 tex=['\\begin{tabular}{lrrrrr}','\\toprule',r'Method & ORCX & MLI-ext. & Both & Worst $R$ & Min. $G$ \\',r'\midrule']
 for r in summary:
  if r['policy']=='strict' and r['method'] in ['residual','binary','full']:tex.append(f"{labels[r['method']]} & {r['openrcx_wins']}/60 & {r['mli_ext_wins']}/60 & {r['beats_both']}/60 & {r['worst_error_ratio']:.4f} & {100*r['minimum_improvement_margin']:.2f}\\% \\\\")
 tex+=['\\bottomrule','\\end{tabular}'];(P/'tables/baseline_consistency.tex').write_text('\n'.join(tex)+'\n')
 lines=['# Baseline consistency (post-hoc)','',f'Unchanged Fig.4 statistic reproduced from raw SSE/SST. Numerical tolerance = {tol:.12g} relative (8 float32 eps); strict and tolerance results are separate. Zero baselines receive no denominator epsilon.','', 'Process/family/component macro weighting and five-mask averaging retained. Cluster resampling retains all masks within each group; 60 conditions are correlated. FEM/transfer have few process-layer groups; intervals are descriptive, not evidence of reliable generalization.','']
 lines += [json.dumps(r) for r in summary]
 lines+=['','## Closest-to-regression cases']+[json.dumps(r) for r in [x for x in margins if x['method']=='full'][:5]]
 (D/'baseline_consistency_report.md').write_text('\n'.join(lines)+'\n')
 worst=next(r for r in margins if r['method']=='full')
 snippet=(r'Full is the only one of the three matched variants whose condition-level point estimates improve over both kernel baselines in every tested cell (Table~\ref{tab:consistency}). This motivates its unified default status, rather than requiring it to minimize every metric. '
          +f"Its narrowest margin is Transfer In/block at 10\\% holdout: {worst['macro_nrmse']:.6f} versus the stronger baseline {worst['stronger_baseline']:.6f}, a {100*worst['improvement_margin']:.2f}\\% reduction. The paired error-difference interval is $[{worst['paired_gap_ci_low']:.5f},{worst['paired_gap_ci_high']:.5f}]$ under a 1,000-replicate layer-group bootstrap; with only two independent layer groups, this is descriptive uncertainty, not evidence that regression risk has been eliminated.\n")
 (P/'tables/baseline_consistency_findings.tex').write_text(snippet)
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(7,2.6))
 for m in ['residual','binary','full']:
  rs=[r for r in cells if r['method']==m];ax.plot(range(60),[r['error_ratio'] for r in rs],label=labels[m],lw=1)
 ax.axhline(1,color='black',ls='--',lw=.8);ax.set(yscale='log',xlabel='All 60 fixed conditions (domain / support / holdout)',ylabel='Error / stronger kernel baseline');ax.legend(ncol=3);fig.tight_layout()
 for ext in ['pdf','png']:fig.savefig(P/f'figures/baseline_consistency.{ext}',dpi=160)
 print(json.dumps(summary,indent=2));print('checks',checks)
if __name__=='__main__':main()
