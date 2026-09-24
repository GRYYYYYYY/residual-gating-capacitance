#!/usr/bin/env python3
"""Analyze real STA exports; generate vector/bitmap figures and manuscript data."""
import csv
import json
import math
from pathlib import Path
import sys
from functools import lru_cache
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle

OUT = Path(sys.argv[1]).resolve()
DATA, FIG = OUT/'data', OUT/'figures'
DATA.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':9, 'axes.titlesize':10,
                     'axes.labelsize':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'svg.fonttype':'none', 'savefig.dpi':220})
COLORS={'linear':'#b85c28','ours':'#007c91'}
LABEL={'linear':'Linear','ours':'Residual gating'}

def read(name, file):
    return pd.read_csv(OUT/'raw'/name/file, sep='\t', keep_default_na=False)

def canon(name):
    return name.replace('\\','')

layout = read('golden','layout.tsv')
layout['key'] = layout.instance.map(canon)
assert layout.key.is_unique, 'ambiguous instance unescaping'
layout['x'] = (layout.xmin+layout.xmax)/2
layout['y'] = (layout.ymin+layout.ymax)/2
lookup = layout.set_index('key')
ports = read('golden','ports.tsv'); ports['key']=ports.port.map(canon)
assert ports.key.is_unique
portlookup=ports.set_index('key')
bounds = np.loadtxt(OUT/'raw/golden/bounds.tsv')

@lru_cache(maxsize=None)
def coord(pin):
    key=canon(pin)
    if key in portlookup.index:
        p=portlookup.loc[key]; return key, float(p.x),float(p.y),'port'
    inst=key.rsplit('/',1)[0]
    if inst in lookup.index:
        p=lookup.loc[inst]; return inst,float(p.x),float(p.y),'instance_center'
    return inst, np.nan,np.nan,'unmapped'

endpoints={}; paths={}
for name in ['golden']+[f'{m}_seed{s}' for s in range(3) for m in ['linear','ours']]:
    d=read(name,'endpoints.tsv')
    assert d.endpoint.is_unique
    d['slack']=pd.to_numeric(d.slack)
    endpoints[name]=d.set_index('endpoint').slack
    p=read(name,'paths.tsv').sort_values(['slack','endpoint','startpoint'],kind='stable')
    p=p.drop_duplicates('endpoint',keep='first').reset_index(drop=True)
    p['signature']=p.pins.map(lambda x:'|'.join(canon(q) for q in x.split('|')))
    p['pair']=p.startpoint+' -> '+p.endpoint
    p['path_delay']=p.arrivals.map(lambda x:float(x.split('|')[-1])-float(x.split('|')[0]))
    p['arrival']=p.arrivals.map(lambda x:float(x.split('|')[-1]))
    p['required']=p.requireds.map(lambda x:float(x.split('|')[-1]))
    p['path_instances']=p.pins.map(lambda x:'|'.join(dict.fromkeys(coord(q)[0] for q in x.split('|'))))
    p.to_csv(DATA/f'critical_paths_{name}.csv',index=False)
    paths[name]=p

allend=pd.concat(endpoints,axis=1).sort_index()
allend.to_csv(DATA/'all_endpoint_slack_including_unconstrained.csv')
coverage=[]
for name,slack in endpoints.items():
    coverage.append(dict(variant=name, reported=len(slack), finite=int(np.isfinite(slack).sum()),
                         unconstrained=int(np.isinf(slack).sum()), missing=int(allend[name].isna().sum())))
pd.DataFrame(coverage).to_csv(DATA/'endpoint_coverage.csv',index=False)
assert allend.notna().all().all(), 'missing endpoint must be investigated'
finite=np.isfinite(allend)
assert (finite.eq(finite.golden,axis=0)).all().all(), 'constraint coverage differs'
common=allend.loc[finite.all(axis=1)].copy()
assert set(common.index)==set(paths['golden'].endpoint)
for name,p in paths.items():
    assert set(p.endpoint)==set(common.index)
    assert np.max(np.abs(p.set_index('endpoint').slack-common[name]))<2e-6

summary=[]; overlaps=[]; gainrows=[]
frames={}
for seed in range(3):
    d=pd.DataFrame({'slack_gold':common.golden,'slack_linear':common[f'linear_seed{seed}'],
                    'slack_ours':common[f'ours_seed{seed}']})
    d[['instance','x','y','coordinate_source']]=[coord(p) for p in d.index]
    d['x']=d.x.astype(float); d['y']=d.y.astype(float)
    assert not d.x.isna().any(), 'unmapped endpoint coordinates'
    for m in ['linear','ours']:
        err=(d[f'slack_{m}']-d.slack_gold).abs()
        d[f'err_{m}']=err
        gt=d.slack_gold<0; pred=d[f'slack_{m}']<0
        cls=np.where(gt,np.where(pred,'TP','FN'),np.where(pred,'FP','TN'))
        d[f'class_{m}']=cls
        counts={x:int(np.sum(cls==x)) for x in ['TP','TN','FP','FN']}
        precision=counts['TP']/(counts['TP']+counts['FP']) if counts['TP']+counts['FP'] else np.nan
        recall=counts['TP']/(counts['TP']+counts['FN']) if counts['TP']+counts['FN'] else np.nan
        summary.append(dict(seed=seed,method=m,endpoints=len(d),mae_ns=err.mean(),rmse_ns=np.sqrt((err**2).mean()),
                            max_error_ns=err.max(),slack_sign_accuracy=np.mean(gt==pred),sign_mismatch_rate=np.mean(gt!=pred),
                            precision=precision,recall=recall,f1=2*precision*recall/(precision+recall),
                            spearman_rho=spearmanr(d.slack_gold,d[f'slack_{m}']).statistic,
                            kendall_tau=kendalltau(d.slack_gold,d[f'slack_{m}']).statistic,**counts))
        for k in [10,20,50,100]:
            g=paths['golden'].head(k); p=paths[f'{m}_seed{seed}'].head(k)
            overlaps.append(dict(seed=seed,method=m,K=k,
                                 endpoint_overlap=len(set(g.endpoint)&set(p.endpoint))/k,
                                 start_end_overlap=len(set(g.pair)&set(p.pair))/k,
                                 full_path_overlap=len(set(g.signature)&set(p.signature))/k))
    d['gain']=d.err_linear-d.err_ours
    eps=2e-6 # exported slack resolution; numerical ties must not count as wins
    gainrows.append(dict(seed=seed,fraction_ours_better=np.mean(d.gain>eps),fraction_linear_better=np.mean(d.gain < -eps),
                         fraction_tied=np.mean(abs(d.gain)<=eps),tie_tolerance_ns=eps,
                         mean_gain_ns=d.gain.mean(),median_gain_ns=d.gain.median(),p90_gain_ns=d.gain.quantile(.9),max_gain_ns=d.gain.max()))
    d.index.name='endpoint'; d.to_csv(DATA/f'endpoint_slack_seed{seed}.csv')
    frames[seed]=d
frames[0].to_csv(DATA/'endpoint_slack.csv')
summary=pd.DataFrame(summary); overlap=pd.DataFrame(overlaps); gains=pd.DataFrame(gainrows)
summary.to_csv(DATA/'summary_metrics.csv',index=False)
summary[['seed','method','TP','TN','FP','FN','precision','recall','f1','slack_sign_accuracy','sign_mismatch_rate']].to_csv(DATA/'violation_metrics.csv',index=False)
overlap.to_csv(DATA/'overlap_metrics.csv',index=False); gains.to_csv(DATA/'gain_metrics.csv',index=False)
summary[['seed','method','spearman_rho','kendall_tau']].to_csv(DATA/'ranking_metrics.csv',index=False)

prov=json.loads((OUT/'provenance.json').read_text())
replays=[]
for name,rec in prov['variants'].items():
    # Sum endpoint minima, never sum multiple paths to the same endpoint.
    assert abs(common[name].min()-rec['worst_slack_ns'])<2e-6
    assert abs(common[name].clip(upper=0).sum()-rec['tns_ns'])<0.02
    replays.append(dict(variant=name,ws_ns=rec['worst_slack_ns'],tns_ns=rec['tns_ns'],
                        original_ws_ns=rec['original_ws_ns'],original_tns_ns=rec['original_tns_ns']))
pd.DataFrame(replays).to_csv(DATA/'global_sta_replay.csv',index=False)

def save(fig,name):
    for ext in ['pdf','svg','png']:
        fig.savefig(FIG/f'{name}.{ext}',bbox_inches='tight',facecolor='white')
    plt.close(fig)

def base(ax,title,background=False):
    if background:
        # Real placed cell bounding boxes; no invented routing image.
        patches=[Rectangle((r.xmin,r.ymin),r.xmax-r.xmin,r.ymax-r.ymin) for r in layout.itertuples()]
        ax.add_collection(PatchCollection(patches,facecolor='#d3d9dd',edgecolor='none',rasterized=True,alpha=.65))
    ax.set(xlim=(bounds[0],bounds[2]),ylim=(bounds[1],bounds[3]),aspect='equal',xlabel='Layout X (µm)',ylabel='Layout Y (µm)')
    ax.set_title(title,loc='left',fontweight='bold',pad=9)
    ax.tick_params(labelsize=8)
    ax.set_xticks([0,400,800,1200]); ax.set_yticks([0,400,800,1200])
    for s in ax.spines.values(): s.set_color('#9aa5af')

D=frames[0]
xedges=np.linspace(bounds[0],bounds[2],51); yedges=np.linspace(bounds[1],bounds[3],51)
count=np.histogram2d(D.x,D.y,bins=(xedges,yedges))[0]
def binned(values,kind='mean'):
    if kind=='mean':
        sums=np.histogram2d(D.x,D.y,bins=(xedges,yedges),weights=values)[0]
        return np.ma.masked_where(count.T==0,(sums/np.maximum(count,1)).T)
    from scipy.stats import binned_statistic_2d
    a=binned_statistic_2d(D.x,D.y,values,statistic='max',bins=(xedges,yedges)).statistic
    return np.ma.masked_invalid(a.T)

vmax=max(float(binned(D.err_linear).max()),float(binned(D.err_ours).max()))
gmax=float(np.max(np.abs(binned(D.gain))))
norm=Normalize(0,vmax); gnorm=TwoSlopeNorm(0,-gmax,gmax)

def heat(ax,values,title,gain=False,kind='mean'):
    base(ax,title)
    ax.set_facecolor('#f1f3f5')
    return ax.pcolormesh(xedges,yedges,binned(values,kind),cmap='RdBu' if gain else 'magma',
                         norm=gnorm if gain else norm,shading='flat',rasterized=False)

fig,axs=plt.subplots(2,2,figsize=(8.5,7.8),layout='constrained')
base(axs[0,0],'(a) Fixed layout and timing endpoints',True)
axs[0,0].scatter(D.x,D.y,s=2,c='#204e66',alpha=.65,rasterized=True)
axs[0,0].text(.035,.965,f'{len(D):,} constrained endpoints\n50% block mask · seed 0',transform=axs[0,0].transAxes,va='top',fontsize=9,bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
for ax,m,letter in [(axs[0,1],'linear','b'),(axs[1,0],'ours','c')]:
    im=heat(ax,D[f'err_{m}'],f'({letter}) {LABEL[m]} |Δslack|')
    fig.colorbar(im,ax=ax,fraction=.045,pad=.025,label='Mean endpoint error (ns)')
    ax.text(.035,.965,f'MAE = {D[f"err_{m}"].mean():.4f} ns',transform=ax.transAxes,va='top',fontsize=9,bbox=dict(facecolor='white',alpha=.92,edgecolor='none'))
im=heat(axs[1,1],D.gain,'(d) Error reduction: Linear − ours',True)
fig.colorbar(im,ax=axs[1,1],fraction=.045,pad=.025,label='Mean error reduction (ns)')
axs[1,1].text(.035,.965,'Blue: ours closer to golden\nRed: Linear closer',transform=axs[1,1].transAxes,va='top',fontsize=9,bbox=dict(facecolor='white',alpha=.92,edgecolor='none'))
save(fig,'fig_downstream_sta_spatial_fidelity')

fig,ax=plt.subplots(figsize=(5,4.6),layout='constrained');base(ax,'Fixed routed database: cell and endpoint positions',True);ax.scatter(D.x,D.y,s=3,c='#204e66');save(fig,'01_layout')
for name,m in [('02_linear_slack_error','linear'),('03_ours_slack_error','ours')]:
    fig,ax=plt.subplots(figsize=(5.4,4.5),layout='constrained');im=heat(ax,D[f'err_{m}'],LABEL[m]+' |Δslack|');fig.colorbar(im,ax=ax,label='Mean endpoint error (ns)');save(fig,name)
fig,ax=plt.subplots(figsize=(5.4,4.5),layout='constrained');im=heat(ax,D.gain,'Error reduction (positive: ours closer)',True);fig.colorbar(im,ax=ax,label='Mean error reduction (ns)');save(fig,'04_improvement_map')
# Scatter diagnostic uses the same scale across both methods, without smoothing.
fig,axs=plt.subplots(1,2,figsize=(9,4),layout='constrained')
scatter_norm=Normalize(0,max(D.err_linear.max(),D.err_ours.max()))
for ax,m in zip(axs,['linear','ours']):
    base(ax,LABEL[m]);im=ax.scatter(D.x,D.y,c=D[f'err_{m}'],s=6,cmap='magma',norm=scatter_norm,rasterized=True)
fig.colorbar(im,ax=axs,label='Endpoint |Δslack| (ns)',shrink=.85);save(fig,'endpoint_scatter')
fig,axs=plt.subplots(1,2,figsize=(9,4),layout='constrained')
maxnorm=Normalize(0,max(D.err_linear.max(),D.err_ours.max()))
for ax,m in zip(axs,['linear','ours']):
    base(ax,LABEL[m]);im=ax.pcolormesh(xedges,yedges,binned(D[f'err_{m}'],'max'),cmap='magma',norm=maxnorm)
fig.colorbar(im,ax=axs,label='Maximum endpoint error per bin (ns)',shrink=.85);save(fig,'maximum_error_maps')

fig,axs=plt.subplots(2,2,figsize=(8.4,7.7),layout='constrained')
for ax,m in zip(axs[0],['linear','ours']):
    base(ax,'(a) Linear violation decisions' if m=='linear' else '(b) Residual-gating decisions',True)
    good=D[f'class_{m}'].isin(['TP','TN']); ax.scatter(D.x[good],D.y[good],s=3,c='#84949f',alpha=.55,label='Correct')
    for cls,marker,c in [('FN','^','#d62728'),('FP','x','#a347ad')]:
        mask=D[f'class_{m}']==cls
        ax.scatter(D.x[mask],D.y[mask],s=45,marker=marker,c=c,label=f'{cls}: {mask.sum()}')
    ax.legend(loc='upper right',fontsize=8,framealpha=.93)
ax=axs[1,0]
for m in ['linear','ours']:
    err=np.sort(D[f'err_{m}']);ax.plot(err,np.arange(1,len(err)+1)/len(err),label=LABEL[m],c=COLORS[m],lw=2)
ax.set(xlabel='Absolute endpoint-slack error (ns)',ylabel='Fraction of endpoints',ylim=(0,1.02));ax.set_title('(c) Endpoint-error distribution',loc='left',fontweight='bold');ax.grid(alpha=.2);ax.legend(fontsize=8)
ax=axs[1,1]
for m in ['linear','ours']:
    sub=overlap[(overlap.seed==0)&(overlap.method==m)]
    ax.plot(sub.K,sub.endpoint_overlap,'o-',color=COLORS[m],label=LABEL[m]+': endpoint')
    ax.plot(sub.K,sub.full_path_overlap,'s--',color=COLORS[m],label=LABEL[m]+': full path')
ax.set(xlabel='K worst-slack endpoints',ylabel='Overlap with golden',xticks=[10,20,50,100],ylim=(0,1.06));ax.set_title('(d) Critical-set agreement',loc='left',fontweight='bold');ax.grid(alpha=.2);ax.legend(fontsize=7.5,loc='lower right')
save(fig,'fig_sta_decision_fidelity')

for m,name in [('linear','05_linear_violation_map'),('ours','06_ours_violation_map')]:
    fig,ax=plt.subplots(figsize=(5.1,4.6),layout='constrained');base(ax,LABEL[m]+' violation classification',True)
    for cls,marker,c,size in [('TP','o','#84949f',3),('TN','o','#327855',6),('FN','^','#d62728',45),('FP','x','#a347ad',45)]:
        mask=D[f'class_{m}']==cls;ax.scatter(D.x[mask],D.y[mask],s=size,marker=marker,c=c,label=f'{cls}: {mask.sum()}')
    ax.legend(fontsize=8);save(fig,name)

# Path geometry is a polyline through actual cell centers/port locations, not wire shapes.
path_coverage=[]
def drawpath(ax,row,color,ls,label,z):
    coords=[coord(p) for p in row.pins.split('|')]
    missing=[p for p,c in zip(row.pins.split('|'),coords) if c[3]=='unmapped']
    path_coverage.append(dict(endpoint=row.endpoint,startpoint=row.startpoint,missing_pins=missing))
    assert not missing, missing
    xy=np.array([(c[1],c[2]) for c in coords])
    keep=np.r_[True,np.any(np.diff(xy,axis=0)!=0,axis=1)];xy=xy[keep]
    ax.plot(xy[:,0],xy[:,1],color=color,ls=ls,lw=2.4 if ls=='-' else 1.5,label=label,zorder=z,alpha=.9)
    ax.scatter(*xy[0],marker='o',s=35,color=color,zorder=z+1)
    ax.scatter(*xy[-1],marker='s',s=35,color=color,zorder=z+1)

fig,axs=plt.subplots(1,2,figsize=(8.7,4.3),layout='constrained')
for ax,m,letter in zip(axs,['linear','ours'],['a','b']):
    base(ax,f'({letter}) Golden vs {LABEL[m]}',True)
    g=paths['golden'].iloc[0];p=paths[f'{m}_seed0'].iloc[0]
    drawpath(ax,g,'#203c56','-','Golden worst path',4)
    drawpath(ax,p,COLORS[m],'--',LABEL[m]+' worst path',5)
    ax.legend(loc='upper left',fontsize=8)
    same=g.signature==p.signature
    ax.text(.025,.025,f'Full path identical: {"yes" if same else "no"}',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.95,edgecolor='none'))
save(fig,'fig_sta_critical_paths')
for m,name in [('linear','07_gold_vs_linear_critical_path'),('ours','08_gold_vs_ours_critical_path')]:
    fig,ax=plt.subplots(figsize=(5.1,4.6),layout='constrained');base(ax,'Golden vs '+LABEL[m],True)
    drawpath(ax,paths['golden'].iloc[0],'#203c56','-','Golden',4);drawpath(ax,paths[f'{m}_seed0'].iloc[0],COLORS[m],'--',LABEL[m],5)
    ax.legend();save(fig,name)
(DATA/'path_coordinate_coverage.json').write_text(json.dumps(path_coverage,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(5.2,3.5),layout='constrained')
for m in ['linear','ours']:
    o=overlap[(overlap.seed==0)&(overlap.method==m)]
    ax.plot(o.K,o.endpoint_overlap,'o-',color=COLORS[m],label=LABEL[m]+': endpoint')
    ax.plot(o.K,o.full_path_overlap,'s--',color=COLORS[m],label=LABEL[m]+': full path')
ax.set(xlabel='K worst-slack endpoints',ylabel='Overlap with golden',xticks=[10,20,50,100],ylim=(0,1.06));ax.legend(fontsize=8);ax.grid(alpha=.2);save(fig,'09_overlap_at_k')

# All seeds side by side: ties and gains remain visible together.
fig,axs=plt.subplots(1,3,figsize=(9.6,2.9),layout='constrained',sharey=True)
for seed,ax in enumerate(axs):
    for m in ['linear','ours']:
        o=overlap[(overlap.seed==seed)&(overlap.method==m)]
        ax.plot(o.K,o.endpoint_overlap,'o-',color=COLORS[m],label=LABEL[m]+': endpoint',markersize=5)
        ax.plot(o.K,o.full_path_overlap,'s--',color=COLORS[m],label=LABEL[m]+': full path',markersize=4)
    ax.set(xlabel='K worst-slack endpoints',xticks=[10,20,50,100],ylim=(.35,1.05))
    ax.set_title(f'Seed {seed}',loc='left',fontweight='bold');ax.grid(alpha=.2)
axs[0].set_ylabel('Overlap with golden')
axs[2].legend(fontsize=6.8,loc='lower left')
save(fig,'fig_sta_overlap_all_seeds')

# Manuscript table: every seed is shown, including less favorable cells.
lines=[r'\begin{tabular}{@{}clrrrrrrrr@{}}',r'\toprule',
       r'Seed & Method & MAE & RMSE & Sign (\%) & FN & FP & EP@50 & Path@50 & $\rho$ \\',r'\midrule']
for r in summary.itertuples():
    o=overlap[(overlap.seed==r.seed)&(overlap.method==r.method)&(overlap.K==50)].iloc[0]
    lines.append(f'{r.seed} & {"Linear" if r.method=="linear" else "Ours"} & {r.mae_ns:.4f} & {r.rmse_ns:.4f} & {100*r.slack_sign_accuracy:.2f} & {r.FN} & {r.FP} & {o.endpoint_overlap:.2f} & {o.full_path_overlap:.2f} & {r.spearman_rho:.5f} '+r'\\')
    if r.method=='ours' and r.seed<2: lines.append(r'\addlinespace')
lines += [r'\bottomrule',r'\end{tabular}']
(OUT.parents[1]/'tables').mkdir(exist_ok=True)
(OUT.parents[1]/'tables/sta_decision_fidelity.tex').write_text('\n'.join(lines)+'\n')

# Original rounded Table 22 values reproduced independently from state records.
g=prov['variants']['golden']; globalrows=[]
for m in ['linear','ours']:
    rs=[prov['variants'][f'{m}_seed{s}'] for s in range(3)]
    globalrows.append(dict(method=m,cap_nrmse_mean=np.mean([r['cap_nrmse'] for r in rs]),
                          max_abs_ws_ns=max(abs(r['original_ws_ns']-g['original_ws_ns']) for r in rs),
                          max_abs_tns_ns=max(abs(r['original_tns_ns']-g['original_tns_ns']) for r in rs)))
pd.DataFrame(globalrows).to_csv(DATA/'table22_reproduction.csv',index=False)
report='''# STA visualization: gf180 / ibex / block 50%\n\nReal fixed-layout replay of the paper_v4 Table 22 audit; no training, rerouting, or ECO.\n\nSpatial figures use seed 0, fixed before examining endpoint results. All three seeds are reported below.\nThe common final ODB, original SDC, Liberty, executable and input SPEFs are hashed in provenance.json.\nAll source audit ODB/SDC hashes agree. Resistance NRMSE is exactly zero for all selected exports.\nGlobal WS/TNS reproduce archived values to their original rounding precision.\n\n## Population and definitions\n\n'''
report+=f'OpenSTA reports {len(allend)} endpoints: {len(common)} constrained, {len(allend)-len(common)} unconstrained in every variant, zero missing. Unconstrained endpoints are retained with Inf in the raw/combined CSV and excluded explicitly from timing metrics. All {len(common)} constrained endpoints have real ODB coordinates. Internal pins use instance centers; output ports use physical pin-box centers.\n\n'
report+='Slacks and errors are in ns; coordinates are µm. Endpoint slack is the minimum setup slack across paths. Exported property values have 1e-6 ns display resolution. An absolute 2e-6 ns tolerance is used only to categorize gain ties; violation labels use the unshifted zero-slack threshold. No SDC or clock changes are introduced.\n\nEP@K compares unique endpoints; start-end overlap compares pin pairs; full-path overlap compares the full ordered data-pin sequence. One worst path per endpoint is used, sorted by slack, endpoint and startpoint; K=10,20,50,100. Rank correlations cover all constrained endpoints. A polyline follows cell centers, not the metal routing.\n\nHeatmaps use identical 50×50 bins and extent. Linear/ours share a zero-based color scale with no clipping. Empty bins are gray, not zero. Gain uses a symmetric diverging scale (blue positive, red negative). Additional scatter and bin-maximum maps are provided.\n\n## Endpoint metrics (all seeds)\n\n'
def md(df):
    rows=['| '+' | '.join(df.columns)+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    for row in df.itertuples(index=False,name=None):
        rows.append('| '+' | '.join(f'{x:.6g}' if isinstance(x,float) else str(x) for x in row)+' |')
    return '\n'.join(rows)
report+=md(summary)+'\n\n## Critical endpoint / path overlap\n\n'+md(overlap)+'\n\n## Gain statistics\n\n'+md(gains)+'\n\n## Table 22 reproduction\n\n'+md(pd.DataFrame(globalrows))+'\n\n'
report+='## Interpretation\n\nResults describe agreement with golden extraction on a fixed routed layout, not timing closure, chip frequency, or signoff accuracy. Endpoint-error, rank and classification claims must be evaluated separately; a reduction in aggregate error does not imply every endpoint or every Top-K set improves.\n'
(OUT/'sta_visualization_summary.md').write_text(report)
print(summary.to_string(index=False));print(overlap.to_string(index=False));print(gains.to_string(index=False))
print('Wrote figures, raw-data CSVs, manuscript table, and summary to',OUT)
