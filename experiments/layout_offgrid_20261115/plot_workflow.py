from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
R=Path(__file__).resolve().parents[2];P=R/'paper/dac_layout_query_revision/figures'
fig,ax=plt.subplots(figsize=(7.1,2.1));ax.set(xlim=(0,10),ylim=(0,4));ax.axis('off')
def box(x,y,w,h,s,c='#edf3f7'):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.06',facecolor=c,edgecolor='#4b606b',lw=.8));ax.text(x+w/2,y+h/2,s,ha='center',va='center',fontsize=8)
def arrow(a,b):ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=1,color='#48535a'))
box(.1,2.6,2,1,'Unmodified routed layout\nNative width / distance calls')
box(3,2.6,2.4,1,'Frozen query census Q\nRaw / effective coordinates')
box(.1,.5,2,1.25,'Characterization samples S\nGeometry, context, capacitance\nSame values for all methods')
box(3,.5,2.4,1.25,'Numerical anchor + Transformer\nUngated / Binary / Full\nFixed weights, fixed query batches')
box(6.3,2.6,3.5,1,'Native query replay\nOriginal rules and returned values','#f7f1e8')
box(6.3,.5,3.5,1.25,'Declared symmetric template P(Q)\nDirect FEM reference, evaluation only\nMaterial/projection contract','#f0f5e8')
arrow((2.1,3.1),(3,3.1));arrow((2.1,1.1),(3,1.1));arrow((4.2,2.6),(4.2,1.75));arrow((5.4,3.1),(6.3,3.1));arrow((5.4,1.1),(6.3,1.1))
ax.text(5,0,'Controlled subsampling and native full-rule fidelity remain separate evaluation protocols.',ha='center',fontsize=7)
for ext in ['pdf','png']:fig.savefig(P/f'method.{ext}',bbox_inches='tight',dpi=200)
