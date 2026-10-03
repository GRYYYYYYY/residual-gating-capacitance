"""1 x 4 version of the original analyze_plot.py spatial-fidelity figure.
Uses archived seed-0 endpoint errors and golden placed-cell boxes; no STA rerun.
Original: test-v1/paper_v5/sta_visualization/analyze_plot.py, lines 145--188.
The 50x50 bins, mean aggregation, bounds and color normalization are unchanged.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
REPO=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--data',type=Path,default=REPO/'results/sta_visualization/gf180_ibex_50')
ap.add_argument('--output',type=Path,default=REPO/'results/my_final_figure3')
args=ap.parse_args()
ROOT=args.data
OUTPUT=args.output
OUTPUT.mkdir(parents=True,exist_ok=False)
with (ROOT/'data/endpoint_slack_seed0.csv').open() as f: rows=list(csv.DictReader(f))
D={k:np.array([float(r[k]) for r in rows]) for k in ['x','y','slack_gold','slack_linear','slack_ours','err_linear','err_ours','gain']}
assert len(rows)==2039
assert all(np.isfinite(v).all() for v in D.values())
np.testing.assert_allclose(D['err_linear'],abs(D['slack_linear']-D['slack_gold']),atol=1e-14)
np.testing.assert_allclose(D['err_ours'],abs(D['slack_ours']-D['slack_gold']),atol=1e-14)
np.testing.assert_allclose(D['gain'],D['err_linear']-D['err_ours'],atol=1e-14)
with (ROOT/'raw/golden/layout.tsv').open() as f: layout=list(csv.DictReader(f,delimiter='\t'))
bounds=np.loadtxt(ROOT/'raw/golden/bounds.tsv')
xedges=np.linspace(bounds[0],bounds[2],51);yedges=np.linspace(bounds[1],bounds[3],51)
count=np.histogram2d(D['x'],D['y'],bins=(xedges,yedges))[0]
def binned(values):
 sums=np.histogram2d(D['x'],D['y'],bins=(xedges,yedges),weights=values)[0]
 return np.ma.masked_where(count.T==0,(sums/np.maximum(count,1)).T)
assert count.sum()==2039
vmax=max(float(binned(D['err_linear']).max()),float(binned(D['err_ours']).max()))
gmax=float(np.max(np.abs(binned(D['gain']))))
norm=Normalize(0,vmax);gnorm=TwoSlopeNorm(0,-gmax,gmax)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.titlesize':10,'axes.labelsize':9,'pdf.fonttype':42,'svg.fonttype':'none'})
fig,axs=plt.subplots(1,4,figsize=(14.6,3.3),layout='constrained')
# Reserve a matching colorbar column even for the physical-layout panel.
def base(ax,title):
 ax.set(xlim=(bounds[0],bounds[2]),ylim=(bounds[1],bounds[3]),aspect='equal')
 ax.set_title(title,loc='left',fontweight='bold',pad=4)
 ax.set_xticks([0,400,800,1200]);ax.set_yticks([0,400,800,1200])
 ax.tick_params(labelsize=8,pad=1,length=2)
 ax.set_xlabel('X (µm)',labelpad=1);ax.set_ylabel('Y (µm)',labelpad=1)
 for spine in ax.spines.values():spine.set_color('#9aa5af')
base(axs[0],'(a) Layout and endpoints')
patches=[Rectangle((float(r['xmin']),float(r['ymin'])),float(r['xmax'])-float(r['xmin']),float(r['ymax'])-float(r['ymin'])) for r in layout]
axs[0].add_collection(PatchCollection(patches,facecolor='#d3d9dd',edgecolor='none',rasterized=True,alpha=.65))
axs[0].scatter(D['x'],D['y'],s=1.25,c='#204e66',alpha=.65,rasterized=True)
axs[0].text(.035,.965,'2,039 endpoints · seed 0',transform=axs[0].transAxes,va='top',fontsize=8,bbox=dict(facecolor='white',alpha=.9,edgecolor='none',pad=2))
dummy=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='magma'),ax=axs[0],fraction=.055,pad=.025)
dummy.ax.set_visible(False)
for ax,m,letter in [(axs[1],'linear','b'),(axs[2],'ours','c')]:
 base(ax,f'({letter}) '+('Linear' if m=='linear' else 'Ours')+' |Δslack|')
 ax.set_facecolor('#f1f3f5')
 im=ax.pcolormesh(xedges,yedges,binned(D['err_'+m]),cmap='magma',norm=norm,shading='flat',rasterized=False)
 cb=fig.colorbar(im,ax=ax,fraction=.055,pad=.025);cb.set_label('Mean error (ns)',labelpad=3);cb.ax.tick_params(labelsize=8,pad=1,length=2)
 ax.text(.035,.965,f'MAE = {D["err_"+m].mean():.4f} ns',transform=ax.transAxes,va='top',fontsize=8,bbox=dict(facecolor='white',alpha=.92,edgecolor='none',pad=2))
base(axs[3],'(d) Error reduction: Linear − ours')
axs[3].set_facecolor('#f1f3f5')
im=axs[3].pcolormesh(xedges,yedges,binned(D['gain']),cmap='RdBu',norm=gnorm,shading='flat',rasterized=False)
cb=fig.colorbar(im,ax=axs[3],fraction=.055,pad=.025);cb.set_label('Reduction (ns)',labelpad=3);cb.ax.tick_params(labelsize=8,pad=1,length=2)
axs[3].text(.035,.965,'Blue: ours closer',transform=axs[3].transAxes,va='top',fontsize=8,bbox=dict(facecolor='white',alpha=.9,edgecolor='none',pad=2))
for ext in ['pdf','png','svg']:
 fig.savefig(OUTPUT/f'fig_downstream_sta_spatial_row.{ext}',bbox_inches='tight',facecolor='white',dpi=220)
(OUTPUT/'spatial_row_checks.json').write_text(json.dumps({'seed':0,'endpoints':len(rows),'bins':[50,50],'mean_absolute_error_linear_ns':float(D['err_linear'].mean()),'mean_absolute_error_ours_ns':float(D['err_ours'].mean()),'shared_error_vmax_ns':vmax,'symmetric_gain_limit_ns':gmax},indent=2)+'\n')
