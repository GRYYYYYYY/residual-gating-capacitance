import json,collections,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];O=R/'results/layout_offgrid_20261115';P=R/'paper/dac_layout_query_revision'
rows=[]
for p in O.glob('predictions_*.jsonl'):rows += [json.loads(l) for l in p.read_text().splitlines()]
metrics=[]
for kind in sorted(set(r['reference_kind'] for r in rows)):
 rr=[r for r in rows if r['reference_kind']==kind]
 for proc,fam in sorted(set((r['process'],r['family']) for r in rr)):
  subset=[r for r in rr if (r['process'],r['family'])==(proc,fam)]
  methods=sorted(set(r['method'] for r in subset))
  sets=[{r['query_id'] for r in subset if r['method']==m and r['status']=='ok'} for m in methods];common=set.intersection(*sets)
  for m in methods:
   rs=[r for r in subset if r['method']==m and r['query_id'] in common and r['status']=='ok']
   if not rs:continue
   truth=np.array([r['reference'] for r in rs]);pred=np.array([r['prediction'] for r in rs]);err=pred-truth
   designs=['all']+sorted(set(d for r in rs for d in r['design_counts']))
   for design in designs:
    for weighting in ['unique','occurrence_HT']:
     weights=np.array([(1. if weighting=='unique' else r['occurrence_count']/r['sampling_probability']) if design=='all' else ((1 if r['design_counts'].get(design,0) else 0) if weighting=='unique' else r['design_counts'].get(design,0)/r['sampling_probability']) for r in rs]);take=weights>0
     if not np.any(take):continue
     for j,name in enumerate(rs[0]['component']):
      w=weights[take];e=err[take,j];y=truth[take,j];sy=np.sum(w*y*y)
      a=np.abs(e);order=np.argsort(a);cw=np.cumsum(w[order])/sum(w)
      quant=lambda z:float(a[order][min(np.searchsorted(cw,z),len(a)-1)])
      metrics.append(dict(reference_kind=kind,process=proc,family=fam,component=name,design=design,weighting=weighting,method=m,n=int(take.sum()),nrmse=float(np.sqrt(np.sum(w*e*e)/sy)) if sy>0 else None,mae=float(np.average(a,weights=w)),signed_error=float(np.average(e,weights=w)),p95_absolute=quant(.95),p99_absolute=quant(.99),max_absolute=float(max(a)),unit=rs[0]['unit'],paired_population=len(common),failed_or_unpaired=sum(r['method']==m for r in subset)-len(rs)))
with (O/'paired_metrics.csv').open('w') as f:
 if metrics:w=csv.DictWriter(f,metrics[0],lineterminator='\n');w.writeheader();w.writerows(metrics)
# Actual native measured distribution: preserve all call classes and denominator.
ms=[json.loads(l) for l in (O/'query_manifest.jsonl').read_text().splitlines()]
cases=sorted(set(r['process']+'/'+r['design'] for r in ms));cls=['on_grid','off_grid_in_support','off_grid_out_of_support','fringe_or_unsupported']
fig,axes=plt.subplots(1,2,figsize=(10,2.8),layout='constrained');bottom=np.zeros(len(cases))
for cl in cls:
 v=np.array([sum(r['occurrence_count'] for r in ms if r['process']+'/'+r['design']==c and r['query_class']==cl) for c in cases]);tot=np.array([sum(r['occurrence_count'] for r in ms if r['process']+'/'+r['design']==c) for c in cases]);v=v/tot*100
 axes[0].bar(range(len(cases)),v,bottom=bottom,label=cl.replace('_',' '));bottom+=v
axes[0].set_xticks(range(len(cases)),[c.replace('ihp-sg13g2','IHP').replace('sky130hs','Sky') for c in cases],rotation=50,ha='right',fontsize=8);axes[0].set_ylabel('Logged call occurrences (%)');axes[0].legend(fontsize=8,loc='lower right')
for cl,col in zip(cls[:3],['#287bb5','#dd8c26','#a04e81']):
 rr=[r for r in ms if r['process']=='asap7' and r['call_type']=='Q' and r['layer']==4 and r['query_class']==cl and 0<r['raw_coordinates'][1]<1]
 axes[1].scatter([r['raw_coordinates'][1] for r in rr],[r['raw_coordinates'][0] for r in rr],s=[3+2*np.log1p(r['occurrence_count']) for r in rr],alpha=.5,label=cl.replace('_',' '),c=col)
supp=json.loads((O/'native_supports.json').read_text())
kn=np.unique(np.array([x[:2] for t in supp.values() if t['process_id']=='asap7' and t['metal']==4 for x in t['coordinates']]),axis=0)
axes[1].scatter(kn[:,1],kn[:,0],marker='x',s=15,c='black',linewidths=.6,label='original knots')
axes[1].set_xlabel('Requested spacing (um), ASAP7 M4');axes[1].set_ylabel('Requested width (um)');axes[1].legend(fontsize=8)
for ext in ['pdf','png']:fig.savefig(P/f'figures/query_census.{ext}',dpi=200)
plt.close(fig)
# Paired direct-reference error by S-only nearest distance, plus frequencies.
plan=json.loads((O/'reference_plan.json').read_text()) if (O/'reference_plan.json').exists() else {'queries':[]}
qs={q['query_id']:q for q in plan['queries']};ts={t['table_id']:t for t in map(json.loads,(R/'runs/reference_dataset_v2/tables.jsonl').read_text().splitlines())}
fig,ax=plt.subplots(1,2,figsize=(10,2.6),layout='constrained');edges=np.array([0,.025,.05,.1,.2,.5,1,np.inf]);dist={}
for qid,q in qs.items():
 x=np.array(ts[q['table_id']]['coordinates']);span=np.ptp(x,axis=0);span[span==0]=1
 dist[qid]=float(np.min(np.linalg.norm((x-np.array(q['coordinates']))/span,axis=1)))
formal=[q for q in qs.values() if q['split']=='formal'];hist=np.zeros(len(edges)-1)
for q in formal:hist[min(np.searchsorted(edges,dist[q['query_id']],side='right')-1,len(hist)-1)]+=q['occurrence_count']/q['sampling_probability']
ax[0].bar(np.arange(len(hist)),hist);ax[0].set_ylabel('HT estimated call occurrences')
for m in ['cmi','anchor','affine','gp','mlp_adapt','binary','full']:
 rr=[r for r in rows if r['reference_kind']=='direct_FEM_template_F_per_m' and r['method']==m and r['status']=='ok'];vals=[]
 for k in range(len(edges)-1):
  rrs=[r for r in rr if edges[k]<=dist[r['query_id']]<edges[k+1]]
  vals.append(np.mean([np.mean(abs(np.array(r['prediction'])-r['reference'])) for r in rrs])*1e12 if rrs else np.nan)
 ax[1].plot(np.arange(len(hist)),vals,'o-',label=m,ms=3)
ax[1].set_ylabel('Mean component absolute error (pF/m)');ax[1].legend(ncol=4,fontsize=8)
labels=['0–.025','.025–.05','.05–.1','.1–.2','.2–.5','.5–1','>1']
for a in ax:a.set_xticks(np.arange(len(hist)),labels,rotation=35,fontsize=8);a.set_xlabel('Nearest S distance (S-span normalized)')
for ext in ['pdf','png']:fig.savefig(P/f'figures/query_errors.{ext}',dpi=200)
plt.close(fig)
# Small same-query table; macro over family and nonzero component groups.
summary=[]
for kind in sorted(set(m['reference_kind'] for m in metrics)):
 for method in sorted(set(m['method'] for m in metrics)):
  for wt in ['unique','occurrence_HT']:
   mm=[m for m in metrics if m['reference_kind']==kind and m['method']==method and m['weighting']==wt and m['design']=='all' and m['nrmse'] is not None]
   if mm:summary.append(dict(reference_kind=kind,method=method,weighting=wt,macro_nrmse=float(np.mean([m['nrmse'] for m in mm])),groups=len(mm)))
(O/'metric_summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
