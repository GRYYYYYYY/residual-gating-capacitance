"""Minimum measured work at the frozen middle threshold, with censor counts.

Medians/IQRs are conditional on attainment, not population guarantees or CIs.
"""
import csv
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=ROOT/'results/dac_characterization_20261114/summary'
rows=list(csv.DictReader((R/'threshold_attainment.csv').open()))
methods=['anchor','affine','gp','mlp_adapt','binary','full']
labels=['Anchor','Affine','GP','Adapted MLP','Binary','Full']
colors=['#666666','#218739','#b34b3c','#cc3377','#6a4c93','#007c91']
fig,axs=plt.subplots(2,3,figsize=(12,6.8),layout='constrained')
for col,setting in enumerate(MODELS):
 for row,field in enumerate(['min_measured_budget','fine_cpu_seconds']):
  ax=axs[row,col]
  for j,method in enumerate(methods):
   rs=[r for r in rows if r['setting']==setting and r['method']==method and r['threshold_index']=='1' and r['zero_truth']=='False']
   hit=[r for r in rs if r['attained']=='True']
   vals=[float(r[field]) for r in hit if r[field]]
   if vals:
    lo,med,hi=np.quantile(vals,[.25,.5,.75]);ax.errorbar(j,med,yerr=[[med-lo],[hi-med]],fmt='o',color=colors[j],capsize=3)
    ax.text(j,hi*1.18,f'{len(hit)}/{len(rs)}',ha='center',fontsize=7,rotation=30)
  ax.set_xticks(range(len(labels)),labels,rotation=40,ha='right',fontsize=8)
  ax.set_title(setting);ax.grid(axis='y',alpha=.2)
  if setting=='public' and row==1:
   ax.text(.5,.5,'Public accesses are simulated.\nSolver CPU cost is unknown.',transform=ax.transAxes,ha='center');ax.set_yticks([])
  else:
   ax.set_yscale('log');ax.margins(y=.45)
  if col==0:ax.set_ylabel('Minimum measured budget' if row==0 else 'Recorded fine-only CPU seconds')
fig.suptitle('Median and IQR among trajectories reaching the frozen error threshold\nLabels: reached / eligible; unachieved trajectories remain censored',fontsize=11)
fig.savefig(R/'fixed_error_cost.pdf');fig.savefig(R/'fixed_error_cost.png',dpi=180)
