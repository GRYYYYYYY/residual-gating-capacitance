"""Compact migration of paper_checked.pdf Table 3 and Figure 3.
Uses existing fixed-node export metrics and STA endpoints; performs no extraction.
Run with experiments/dac_characterization_20261114/env.sh sourced.
"""
from pathlib import Path
import csv,gzip,json,re
from decimal import Decimal
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent; R=P.parents[1]; D=P/'data/downstream_fidelity'
rows=list(csv.DictReader((P/'tables/native_missingness.csv').open()))
idx={(r['platform'],r['design'],float(r['ratio']),r['method']):r for r in rows}
fields=['capacitance_nrmse_mean','max_abs_ws_ns','max_abs_tns_ns']
# Verify every displayed value in the supplied Table 3 against its unrounded CSV.
case=['','','']; checked=0
for line in (D/'main_downstream_compact.tex').read_text().splitlines():
 line=re.sub(r'\\textbf\{([^{}]*)\}',r'\1',line)
 cols=[x.strip() for x in line.replace(r'\\','').split('&')]
 if len(cols)!=7 or cols[3] not in ['Linear','Ours']:continue
 for i in range(3):
  if cols[i]:case[i]=cols[i]
 row=idx[case[0],case[1].lower(),float(case[2].replace(r'\%',''))/100,'linear' if cols[3]=='Linear' else 'ours']
 assert int(row['seeds'])==3
 for field,value in zip(fields,cols[4:]):
  tol=0.500001*10**Decimal(value).as_tuple().exponent if float(value)!=0 else 1e-15
  assert abs(float(row[field])-float(value))<=tol+1e-15,(case,field,row[field],value)
  checked+=1
assert checked==96
names={'asap7':'ASAP7','gf180':'GF180','ihp-sg13g2':'IHP','sky130hs':'Sky130HS'}
raw=[];tex=[r'\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lrrr@{}}',r'\toprule',r'Layout & Cap. & $|\Delta\mathrm{WS}|$ & $|\Delta\mathrm{TNS}|$ \\',r'\midrule']
for platform,label in names.items():
 for design in ['aes','ibex']:
  reductions=[]
  for ratio in [.3,.5]:
   base=idx[platform,design,ratio,'linear'];full=idx[platform,design,ratio,'ours']
   record=dict(platform=platform,design=design,holdout=ratio,seeds=3)
   vals=[]
   for field in fields:
    l=float(base[field]);o=float(full[field]);gain=100*(1-o/l) if l else None
    if not l:assert o==0
    record.update({field+'_linear':l,field+'_full':o,field+'_reduction_pct':gain})
    vals.append(gain)
   raw.append(record);reductions.append(vals)
  cells=[]
  for j in range(3):
   v=[r[j] for r in reductions]
   cells.append(r'$0\!\to\!0$' if all(x is None for x in v) else '/'.join(f'{x:.1f}' for x in v))
  tex.append(' & '.join([label+'/'+design.upper()]+cells)+r' \\')
tex += [r'\bottomrule',r'\end{tabular*}']
(P/'tables/downstream_fidelity_compact.tex').write_text('\n'.join(tex)+'\n')
with (D/'downstream_reductions.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
assert all(r[f+'_reduction_pct']>0 for r in raw for f in fields[:2])
assert sum(r[fields[2]+'_reduction_pct'] is None for r in raw)==4
assert all(r[fields[2]+'_reduction_pct']>0 for r in raw if r[fields[2]+'_reduction_pct'] is not None)

with (R/'results/sta_visualization/gf180_ibex_50/data/endpoint_slack_seed0.csv').open() as f:er=list(csv.DictReader(f))
v={k:np.array([float(r[k]) for r in er]) for k in ['x','y','slack_gold','slack_linear','slack_ours','err_linear','err_ours','gain']}
assert len(er)==2039 and all(np.isfinite(x).all() for x in v.values())
np.testing.assert_allclose(v['err_linear'],abs(v['slack_linear']-v['slack_gold']),atol=1e-14)
np.testing.assert_allclose(v['err_ours'],abs(v['slack_ours']-v['slack_gold']),atol=1e-14)
np.testing.assert_allclose(v['gain'],v['err_linear']-v['err_ours'],atol=1e-14)
with gzip.open(D/'layout.tsv.gz','rt') as f:layout=list(csv.DictReader(f,delimiter='\t'))
bounds=np.loadtxt(D/'bounds.tsv');edges=[np.linspace(bounds[k],bounds[k+2],51) for k in [0,1]]
count=np.histogram2d(v['x'],v['y'],bins=edges)[0];assert count.sum()==2039
# Identical 50x50 averaging and normalization to the original, with ns -> ps units.
def binned(a):
 sums=np.histogram2d(v['x'],v['y'],bins=edges,weights=a*1000)[0]
 return np.ma.masked_where(count.T==0,(sums/np.maximum(count,1)).T)
linear=binned(v['err_linear']);full=binned(v['err_ours']);gain=binned(v['gain'])
vmax=max(float(linear.max()),float(full.max()));gmax=float(np.max(np.abs(gain)))
np.testing.assert_allclose([vmax,gmax],[10.495999999999839,6.235999999999464],rtol=1e-12)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'axes.titlesize':7.5,'axes.labelsize':7,'pdf.fonttype':42})
fig=plt.figure(figsize=(7.1,1.72))
gs=fig.add_gridspec(1,6,width_ratios=[1,1,1,.045,1,.045],left=.055,right=.975,bottom=.23,top=.85,wspace=.21)
axs=[fig.add_subplot(gs[0,i]) for i in [0,1,2,4]]
for i,(ax,title) in enumerate(zip(axs,['(a) Placement','(b) Linear error','(c) Full error','(d) Error reduction'])):
 ax.set(xlim=(bounds[0],bounds[2]),ylim=(bounds[1],bounds[3]),aspect='equal')
 ax.set_title(title,pad=4);ax.set_xticks([0,500,1000]);ax.set_yticks([0,500,1000]);ax.tick_params(labelsize=6.5,pad=1,length=2)
 ax.set_facecolor('#ededed')
 if i:ax.set_yticklabels([])
 else:ax.set_ylabel(r'$y$ ($\mu$m)',labelpad=1)
 for spine in ax.spines.values():spine.set_color('#9aa5af')
patches=[Rectangle((float(r['xmin']),float(r['ymin'])),float(r['xmax'])-float(r['xmin']),float(r['ymax'])-float(r['ymin'])) for r in layout]
axs[0].add_collection(PatchCollection(patches,facecolor='#c7cdd2',edgecolor='none',rasterized=True,alpha=.65))
axs[0].scatter(v['x'],v['y'],s=.45,c='#204e66',alpha=.65,rasterized=True)
axs[0].text(.03,.97,'2,039 endpoints',transform=axs[0].transAxes,va='top',fontsize=6,bbox=dict(facecolor='white',alpha=.88,edgecolor='none',pad=1))
norm=Normalize(0,vmax)
for ax,a,field in [(axs[1],linear,'err_linear'),(axs[2],full,'err_ours')]:
 im=ax.pcolormesh(*edges,a,cmap='magma',norm=norm,shading='flat',rasterized=True)
 ax.text(.03,.97,f'MAE {1000*v[field].mean():.2f} ps',transform=ax.transAxes,va='top',fontsize=6,bbox=dict(facecolor='white',alpha=.9,edgecolor='none',pad=1))
cb=fig.colorbar(im,cax=fig.add_subplot(gs[0,3]));cb.set_ticks([0,5,10]);cb.ax.tick_params(labelsize=6,pad=1,length=2);cb.ax.set_title('ps',fontsize=6.5,pad=3)
im=axs[3].pcolormesh(*edges,gain,cmap='RdBu',norm=TwoSlopeNorm(0,-gmax,gmax),shading='flat',rasterized=True)
cb=fig.colorbar(im,cax=fig.add_subplot(gs[0,5]));cb.set_ticks([-6,0,6]);cb.ax.tick_params(labelsize=6,pad=1,length=2);cb.ax.set_title('ps',fontsize=6.5,pad=3)
fig.text(.5,.04,r'$x$ ($\mu$m)',ha='center',fontsize=7)
for ext in ['pdf','png']:fig.savefig(P/f'figures/downstream_spatial_compact.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
plt.close(fig)
checks={'verified_original_table_cells':checked,'layout_holdout_pairs':len(raw),'capacitance_improved':16,'worst_slack_improved':16,'tns_improved':12,'tns_zero_ties':4,'finite_seed0_endpoints':2039,'spatial_bins':[50,50],'mae_linear_ps':float(1000*v['err_linear'].mean()),'mae_full_ps':float(1000*v['err_ours'].mean()),'mae_reduction_pct':float(100*(1-v['err_ours'].mean()/v['err_linear'].mean())),'shared_error_vmax_ps':vmax,'symmetric_gain_limit_ps':gmax,'scope':'fixed-node rule export; spatial maps are seed 0, table aggregates three seeds'}
(D/'verification.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
