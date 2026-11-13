import json,csv,collections
from common import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
R=ROOT/'results/dac_characterization_20261114/summary'
fig,ax=plt.subplots(figsize=(10.4,2.5));ax.axis('off');ax.set(xlim=(0,10.4),ylim=(0,2.5))
boxes=[(.1,1.0,'Candidate geometry\n+ material stack'),(2.2,1.0,'B observed geometries\nS and y(S)'),(4.3,1.0,'Offline completion\nanchor + residual'),(6.4,1.0,'Native rule file\nretain observed rows'),(8.5,1.0,'Fixed-layout\nOpenRCX → STA')]
for x,y,text in boxes:
 ax.add_patch(FancyBboxPatch((x,y),1.8,1.,boxstyle='round,pad=0.03',facecolor='#edf4f4',edgecolor='#007c91'))
 ax.text(x+.9,y+.5,text,ha='center',va='center',fontsize=9)
for x in [1.9,4.,6.1,8.2]:ax.annotate('',xy=(x+.28,1.5),xytext=(x,1.5),arrowprops=dict(arrowstyle='->',color='#444444'))
ax.text(5.2,.4,'Sealed Q evaluates completion; full-rule extraction evaluates downstream fidelity.\nCount unique geometry queries, recorded solver CPU work, and measured completion cost separately.',ha='center',fontsize=10)
fig.tight_layout();fig.savefig(R/'workflow.pdf');fig.savefig(R/'workflow.png',dpi=180);plt.close(fig)
rows=list(csv.DictReader((R/'budget_curves.csv').open()));styles={'full':('#007c91','Full'),'binary':('#6a4c93','Binary'),'mlp_adapt':('#cc3377','Adapted MLP'),'anchor':('#666666','Anchor'),'gp':('#b34b3c','GP')}
fig,axs=plt.subplots(1,3,figsize=(11.5,3.6),layout='constrained')
for ax,s in zip(axs,MODELS):
 for method,(color,label) in styles.items():
  rr=sorted([r for r in rows if r['setting']==s and r['method']==method and r['strategy']=='farthest'],key=lambda r:int(r['budget']))
  ax.plot([float(r['mean_completion_wall_seconds']) for r in rr],[float(r['nrmse']) for r in rr],'o-',color=color,label=label)
 ax.set(title=s,xlabel='Completion + target adaptation (s/table)',ylabel='Macro NRMSE',xscale='log',yscale='log');ax.grid(alpha=.2)
fig.legend(*axs[-1].get_legend_handles_labels(),loc='outside lower center',ncol=5);fig.savefig(R/'completion_cost.pdf');fig.savefig(R/'completion_cost.png',dpi=180);plt.close(fig)
if (R/'downstream_means.csv').exists():
 ds=list(csv.DictReader((R/'downstream_means.csv').open()));cases=sorted({r['case'] for r in ds});fig,axs=plt.subplots(2,1,figsize=(11,6),layout='constrained')
 for ax,metric,label in zip(axs,['net_cap_nrmse','ws_abs_ns'],['Net capacitance NRMSE','Absolute WS difference (ns)']):
  for j,m in enumerate(['cmi','anchor','affine','binary','full']):
   vals=[float(next(r[metric] for r in ds if r['case']==c and r['method']==m and int(r['budget'])==4)) for c in cases]
   ax.bar(np.arange(len(cases))+(j-2)*.16,vals,.15,label=m)
  ax.set_xticks(range(len(cases)),cases,rotation=25,ha='right');ax.set_ylabel(label);ax.set_yscale('symlog',linthresh=1e-5);ax.grid(axis='y',alpha=.2)
 axs[0].legend(ncol=5);fig.savefig(R/'native_fidelity_B4.pdf');fig.savefig(R/'native_fidelity_B4.png',dpi=180);plt.close(fig)
