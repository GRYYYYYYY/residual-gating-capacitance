from common import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=ROOT/'results/dac_characterization_20261114';S=R/'summary';S.mkdir(exist_ok=True)
rows=json.loads((R/'member_sensitivity/summary.json').read_text());fig,axs=plt.subplots(1,3,figsize=(11,3.4),layout='constrained')
for ax,s in zip(axs,MODELS):
 for method,color in [('full','#007c91'),('binary','#6a4c93'),('residual','#c17d11')]:
  budgets=sorted({r['budget'] for r in rows if r['setting']==s});means=[];low=[];high=[]
  for b in budgets:
   vals=[r['nrmse'] for r in rows if r['setting']==s and r['method']==method and r['budget']==b];means.append(np.mean(vals));low.append(min(vals));high.append(max(vals))
  ax.plot(budgets,means,'o-',color=color,label=method);ax.fill_between(budgets,low,high,color=color,alpha=.13)
 ax.set(title=s,xlabel='Unique observed geometries',ylabel='Member macro NRMSE',xscale='log',yscale='log');ax.grid(alpha=.2)
fig.legend(*axs[-1].get_legend_handles_labels(),loc='outside lower center',ncol=3);fig.savefig(S/'gating_training_seeds.pdf');fig.savefig(S/'gating_training_seeds.png',dpi=180)
print('three training seeds, data seed11; shaded min-max, not CI')
