from common import *
os.sched_setaffinity(0,{26})
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
fig,ax=plt.subplots(figsize=(7.1,1.8));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
plt.rcParams.update({'pdf.fonttype':42,'font.family':'DejaVu Sans'})
def box(x,y,w,h,txt,color):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012',facecolor=color,edgecolor='#52606b',lw=.8));ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=8)
def arrow(a,b,style='-'):
 ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':1,'color':'#36454f','linestyle':style})
ax.text(.33,.96,'Table preparation',ha='center',va='top',fontsize=9,fontweight='bold');ax.text(.85,.96,'Native extraction',ha='center',va='top',fontsize=9,fontweight='bold')
ax.axvline(.68,ymin=.08,ymax=.87,color='#888888',ls='--',lw=.8)
box(.015,.52,.145,.23,'Characterized S','#e5edf7');box(.21,.52,.17,.23,'Native table\nconstruction','#e8f0e7');box(.47,.52,.17,.23,'computeTable','#e8f0e7')
box(.21,.08,.24,.23,'Full / Binary\nsame S, canonical slot Q*','#f6e4dd');box(.72,.52,.12,.23,'Native\ngetter','#e8f0e7');box(.885,.52,.10,.23,'RC /\nSPEF','#e8f0e7')
arrow((.16,.635),(.21,.635));arrow((.38,.635),(.47,.635));arrow((.64,.635),(.72,.635));arrow((.84,.635),(.885,.635))
arrow((.09,.52),(.21,.20));arrow((.45,.20),(.55,.52));ax.text(.51,.20,'Eligible\ncapacitances',fontsize=7,ha='left',va='center');ax.text(.785,.27,'Layout Q',fontsize=8,ha='center');arrow((.785,.37),(.785,.52))
ax.text(.34,.405,'Keep measurements, R and special paths',ha='center',fontsize=7.5)
fig.subplots_adjust(left=.005,right=.995,bottom=.02,top=.98)
for ext in ['pdf','png']:fig.savefig(R/f'paper/dac_layout_query_revision/figures/compute_table_interface.{ext}',dpi=180,bbox_inches='tight')
