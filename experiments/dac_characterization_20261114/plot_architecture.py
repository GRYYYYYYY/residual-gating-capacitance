from common import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
out=ROOT/'results/dac_characterization_20261114/summary';out.mkdir(exist_ok=True)
fig,ax=plt.subplots(figsize=(9,3.1));ax.set(xlim=(0,9),ylim=(0,3.1));ax.axis('off')
def box(x,y,w,h,text):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.04',edgecolor='#007c91',facecolor='#edf4f4'));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=9)
box(.1,1.05,1.55,1,'Geometry, context,\nS and y(S)')
box(2.,1.85,2.,.8,'Support anchor b\n+ numeric corrections')
box(2.,.35,2.,.8,'Shared Transformer\nresidual + fusion weights')
box(4.55,1.05,1.7,1,'b + weighted\ncorrections')
box(6.8,1.05,2.,1,'Nonnegative output\nexact observations')
for start,end in [((1.65,1.7),(2.,2.15)),((1.65,1.35),(2.,.75)),((4.,2.15),(4.55,1.7)),((4.,.75),(4.55,1.35)),((6.25,1.55),(6.8,1.55))]:ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='->',color='#444'))
ax.text(4.5,2.92,'GP length multipliers: 0.5, 1, 2; ridges: 1e-6, 1e-4',ha='center',fontsize=10)
ax.text(6.65,.35,'Full computes applicable branches before fusion.\nPruning is a separate ablation, not automatic scheduling.',ha='center',fontsize=9)
fig.tight_layout();fig.savefig(out/'architecture.pdf');fig.savefig(out/'architecture.png',dpi=180)
