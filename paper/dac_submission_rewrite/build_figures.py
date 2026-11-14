"""Read existing score records and draw publication figures; no model execution."""
from pathlib import Path
import csv,gzip,json,hashlib,runpy
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
P=Path(__file__).resolve().parent; R=P.parents[1]; F=P/'figures'; T=P/'tables'
for d in [F,T]:d.mkdir(exist_ok=True)
inputs={}
def ref(p):
 p=R/p; inputs[str(p.relative_to(R))]=hashlib.sha256(p.read_bytes()).hexdigest();return p
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.labelsize':9,'axes.titlesize':10,'legend.fontsize':8,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
colors={'full':'#b34332','binary':'#176394','mlp_adapt':'#8d5c9c','gp':'#2e8870','affine':'#b0802d','cmi':'#777777','residual':'#282828','cnp':'#aa69a1'}
labels={'full':'Full fusion','binary':'Binary gate','residual':'Ungated residual','anchor':'Anchor','cmi':'CMI','gp':'RBF-GP','affine':'Local affine','mlp_adapt':'Adapted MLP','cnp':'CNP','attentioncap_adapted':'Adapted AttentionCap'}
def save(fig,name):
 fig.savefig(F/(name+'.pdf'),bbox_inches='tight');fig.savefig(F/(name+'.png'),bbox_inches='tight',dpi=170);plt.close(fig)
def tabular(name,head,rows,fmt):
 s='\\begin{tabular}{'+fmt+'}\n\\toprule\n'+' & '.join(head)+r' \\'+'\n\\midrule\n'
 s+='\n'.join(' & '.join(map(str,r))+r' \\' for r in rows)+'\n\\bottomrule\n\\end{tabular}\n';(T/(name+'.tex')).write_text(s)
# Exact mean-mask arithmetic; same released record aggregator as published tables.
agg=runpy.run_path(str(ref(Path('scripts/verify_final_paper.py'))))['aggregate']
summary=json.load(open(ref(Path('experiments/paper_controls/comparison_summary.json'))))
conditions=['inside/mcar','inside/block','outside/mcar','outside/block','outside/extrapolation']
cn=['In/random','In/block','Out/random','Out/block','Boundary']
rows=[]
for domain in ['public','reference','to_asap7']:
 base=Path('experiments/paper_controls/scores')/domain
 a=agg(ref(base/'learned_confirmation.jsonl.gz')); b=agg(ref(base/'baseline_confirmation.jsonl.gz')); c=agg(ref(base/'affine_confirmation.jsonl.gz'))
 selected=json.load(open(ref(base/'affine_selection.json')))['selected']
 for condition in conditions:
  vals={m:a['full_replayed' if m=='full' else m,'ensemble',condition] for m in ['full','binary','residual']}
  for m in vals:assert abs(vals[m]-summary[domain][m][condition])<1e-12
  vals['affine']=c[selected,'ensemble',condition]
  vals['anchor']=summary[domain]['anchor'][condition]
  for m in ['cmi','gp','pchip','idw','openrcx_li']:
   key=('cmi1d' if domain=='public' else 'cmi2d') if m=='cmi' else m
   vals[m]=next(v for (mm,seed,cc),v in b.items() if mm==key and cc==condition)
  rows.append(dict(domain=domain,condition=condition,**vals))
missing=pd.DataFrame(rows);missing.to_csv(T/'fixed_missingness.csv',index=False)
# Every Full/CMI claim reproduced before any figure is constructed.
assert (missing.full<missing.cmi).sum()==15
assert (missing[missing.domain=='reference'].full<missing[missing.domain=='reference'].binary).all()
texrows=[]
for domain,dl in [('public','Public'),('reference','FEM'),('to_asap7','Transfer')]:
 for cond,cl in zip(conditions,cn):
  r=missing[(missing.domain==domain)&(missing.condition==cond)].iloc[0];ms=['cmi','anchor','affine','gp','residual','binary','full'];best=min(r[m] for m in ms)
  vs=[r'\textbf{'+f'{r[m]:.4f}'+'}' if r[m]==best else f'{r[m]:.4f}' for m in ms]
  texrows.append([dl,cl]+vs)
tabular('fixed_missingness',['Data','Queries','CMI','Anchor','Affine','RBF-GP','Ungated','Binary','Full'],texrows,'llrrrrrrr')
# Main fixed-budget population and all completed learning controls.
budget=pd.read_csv(ref(Path('review/dac_capacitance_20261114/same_budget.csv')))
budget.to_csv(T/'fixed_budget_all.csv',index=False)
fig,axs=plt.subplots(1,3,figsize=(7.05,2.18));fig.subplots_adjust(left=.075,right=.99,bottom=.24,top=.80,wspace=.32)
for ax,(d,title) in zip(axs,[('public','(a) Public rules'),('reference','(b) FEM reference'),('to_asap7','(c) Transfer to ASAP7')]):
 for m in ['cmi','affine','gp','mlp_adapt','binary','full']:
  x=budget[(budget.setting==d)&(budget.method==m)].sort_values('budget');ax.plot(x.budget,x.macro_nrmse,marker='o',ms=3,lw=1.3,color=colors[m],label=labels[m])
 ax.set(xscale='log',yscale='log',xlabel='Observed geometries B',title=title);ax.set_xticks(sorted(x.budget));ax.set_xticklabels([str(int(b)) for b in sorted(x.budget)]);ax.grid(alpha=.15,which='major');ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
axs[0].set_ylabel('Pooled-replicate NRMSE');fig.legend(*axs[0].get_legend_handles_labels(),loc='upper center',ncol=6,frameon=False,columnspacing=.9,handlelength=1.4)
save(fig,'budget_accuracy')
aux=[]
for d,dl in [('public','Public'),('reference','FEM'),('to_asap7','Transfer')]:
 for m in ['residual','cnp','attentioncap_adapted']:
  x=budget[(budget.setting==d)&(budget.method==m)].set_index('budget')
  aux.append([dl,{'residual':'Ungated','cnp':'CNP','attentioncap_adapted':'Adapted AC'}[m]]+[f'{x.loc[b,"macro_nrmse"]:.4f}' if b in x.index else '--' for b in [4,8,16,32,64]])
tabular('budget_aux',['Data','Method','4','8','16','32','64'],aux,'llrrrrr')
# All native conditions, separately defined statistics for each protocol.
nj=json.load(open(ref(Path('runs/downstream_holdout_v1/summary.json'))));nfix=pd.DataFrame(nj['cells']);nfix.to_csv(T/'native_missingness.csv',index=False)
nb=pd.read_csv(ref(Path('paper/dac_evidence_closeout_20261114/native_all_layouts_all_metrics.csv')));nb.to_csv(T/'native_budget.csv',index=False)
cases=[p+'/'+d for p in ['asap7','gf180','ihp-sg13g2','sky130hs'] for d in ['aes','ibex']]
fig,axs=plt.subplots(2,3,figsize=(7.05,3.8));fig.subplots_adjust(left=.09,right=.99,top=.88,bottom=.16,hspace=.45,wspace=.32)
short=['A','G','I','S'];xt=[f'{p}{d}{b}' for p in short for d in ['a','i'] for b in ['4','8']]
xtf=[f'{p}{d}{b}' for p in short for d in ['a','i'] for b in ['3','5']]
for j,(metric,title,factor) in enumerate([('capacitance_nrmse_mean','Net-C NRMSE',1),('max_abs_ws_ns','Max absolute WS error (ps)',1000),('max_abs_tns_ns','Max absolute TNS error (ps)',1000)]):
 for m,l,c in [('linear','CMI',colors['cmi']),('ours','Full fusion',colors['full'])]:
  vals=[float(nfix[(nfix.platform==case.split('/')[0])&(nfix.design==case.split('/')[1])&(nfix.ratio==b)&(nfix.method==m)].iloc[0][metric])*factor for case in cases for b in [.3,.5]]
  axs[0,j].plot(range(16),vals,'.-',ms=3,lw=1,color=c,label=l)
 axs[0,j].set(title=title,yscale='symlog' if j==2 else 'log',xticks=range(16));axs[0,j].set_xticklabels(xtf,rotation=90,fontsize=7);axs[0,j].grid(alpha=.15)
for j,(metric,title,factor) in enumerate([('net_cap_nrmse','Net-C NRMSE',1),('ws_abs_ns','Absolute WS error (ps)',1000),('slack_p99_ns','P99 absolute slack error (ps)',1000)]):
 for m in ['cmi','binary','full']:
  vals=[float(nb[(nb.case==case)&(nb.budget==b)&(nb.method==m)].iloc[0][metric])*factor for case in cases for b in [4,8]]
  axs[1,j].plot(range(16),vals,'.-',ms=3,lw=1,color=colors[m],label=labels[m])
 axs[1,j].set(title=title,yscale='log',xticks=range(16));axs[1,j].set_xticklabels(xt,rotation=90,fontsize=7);axs[1,j].grid(alpha=.15)
fig.legend(*axs[1,0].get_legend_handles_labels(),loc='upper center',ncol=3,frameon=False)
fig.text(.002,.73,'Fixed missingness',rotation=90,va='center',fontsize=8);fig.text(.002,.32,'Fixed budget',rotation=90,va='center',fontsize=8)
save(fig,'native_fidelity')
# Support analysis: individual members; no ensemble re-scoring.
mech=pd.read_csv(ref(Path('paper/dac_evidence_closeout_20261114/mechanism_budget.csv')));mech.to_csv(T/'support_protocol.csv',index=False)
ret=pd.read_csv(ref(Path('paper/dac_evidence_closeout_20261114/retention.csv')));ret.to_csv(T/'retention.csv',index=False)
fig,ax=plt.subplots(figsize=(3.4,2.05));fig.subplots_adjust(left=.20,right=.98,bottom=.25,top=.77)
z=mech.iloc[:4].copy();z['B']=z.B.astype(int)
for col,label,color,ls in [('Full-0','Full source','#b34332','--'),('Full-H','Full H','#b0802d',':'),('Full-L','Full L','#b34332','-'),('binary-L','Binary L','#176394','-')]:
 ax.plot(z.B,z[col],marker='o',ms=3,label=label,color=color,ls=ls,lw=1.3)
ax.set(xscale='log',xticks=[4,8,16,32],xlabel='Observed geometries B',ylabel='Group-balanced NRMSE');ax.set_xticklabels(['4','8','16','32']);ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator());ax.grid(alpha=.15);fig.legend(*ax.get_legend_handles_labels(),loc='upper center',ncol=2,frameon=False);save(fig,'support_protocol')
z=missing[missing.domain=='reference'];gain=100*(1-z.full/z.binary)
(T/'fem_gain_range.tex').write_text(f'{gain.min():.1f}--{gain.max():.1f}'+r'\%')
# Geometry from the recorded first table and its actual farthest-first history.
geo=ref(Path('runs/round3_evaluation_inputs_v1/reference_confirmation_round3_main.jsonl'))
tables=[json.loads(x) for x in geo.read_text().splitlines()]
recfile=ref(Path('results/dac_characterization_20261114/confirmation_reference/records.jsonl.gz'))
with gzip.open(recfile,'rt') as f:
 for line in f:
  r=json.loads(line)
  if r['strategy']=='farthest' and r['budget']==8 and r['data_seed']==11:
   record=r;break
t=next(t for t in tables if t['table_id']==record['table_id']);x=np.asarray(t['coordinates']);history=record['history'];q=record['query_indices']
(T/'geometry_example.json').write_text(json.dumps({'table_id':t['table_id'],'coordinates':t['coordinates'],'support_order':history,'sealed_queries':q,'data_seed':11},indent=2))
fig=plt.figure(figsize=(7.05,2.85));gs=fig.add_gridspec(1,3,width_ratios=[1,1.35,1],left=.01,right=.99,bottom=.18,top=.91,wspace=.34)
a=fig.add_subplot(gs[0]);a.set(xlim=(0,1),ylim=(0,1));a.axis('off')
def box(ax,x,y,w,h,s,color='#eaf2f6',fs=8):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.01',edgecolor='#526675',facecolor=color,lw=.7));ax.text(x+w/2,y+h/2,s,ha='center',va='center',fontsize=fs)
def arrow(ax,p,q):ax.annotate('',xy=q,xytext=p,arrowprops=dict(arrowstyle='->',lw=.9,color='#34485e'))
a.set_title('(a) Rule-to-timing interface',fontsize=9)
for y,s in [(.79,'Geometry + context\nObserved capacitances'),(.54,'Complete query entries\nPreserve observations'),(.29,'Native rule file\nOpenRCX → SPEF'),(.04,'Fixed layout + libraries\nSTA fidelity to full rules')]:box(a,.04,y,.92,.17,s)
for y in [.79,.54,.29]:arrow(a,(.5,y),(.5,y-.08))
a=fig.add_subplot(gs[1]);a.set(xlim=(0,1),ylim=(0,1));a.axis('off');a.set_title('(b) Shared residual predictor',fontsize=9)
box(a,.02,.80,.96,.16,'Geometry / support-value tokens\nStructure / material tokens');box(a,.02,.53,.57,.15,'Shared Transformer\nNeural correction');box(a,.68,.53,.3,.15,'Support\nanchor');arrow(a,(.30,.80),(.30,.69));arrow(a,(.82,.80),(.82,.69))
box(a,.02,.21,.43,.2,'Binary gate\nZero + neural',color='#e5eff7');box(a,.55,.21,.43,.2,'Full fusion\nNumerical +\nneural',color='#faece8');arrow(a,(.30,.53),(.24,.42));arrow(a,(.35,.53),(.74,.42));arrow(a,(.82,.53),(.80,.42));arrow(a,(.82,.53),(.39,.42));a.text(.50,.04,'Anchor + gated correction → nonnegative C',ha='center',fontsize=8)
a=fig.add_subplot(gs[2]);a.set_title('(c) Actual coverage order',fontsize=9)
a.scatter(x[:,0],x[:,1],s=7,c='#cbd2d8');a.scatter(x[q,0],x[q,1],s=10,marker='x',c='#777777')
a.plot(x[history,0],x[history,1],color='#176394',lw=.7,alpha=.6);a.scatter(x[history,0],x[history,1],s=23,c='#176394')
for k,i in enumerate(history):a.annotate(str(k+1),(x[i,0],x[i,1]),xytext=(3,2),textcoords='offset points',fontsize=7)
a.set(xlabel='Width (µm)',ylabel='Spacing (µm)');a.text(.5,-.32,'ASAP7 M7 DIAGUNDER; B = 8',ha='center',transform=a.transAxes,fontsize=7)
save(fig,'method')
# Family/component view, same budget aggregation; additional editable result.
comp=pd.read_csv(ref(Path('results/dac_characterization_20261114/summary/component_metrics.csv')))
comp=comp[(comp.strategy=='farthest')&comp.method.isin(['full','binary','gp','mlp_adapt'])];comp.to_csv(T/'component_family.csv',index=False)
fig,axs=plt.subplots(1,3,figsize=(7.05,2.4),layout='constrained')
for ax,d in zip(axs,['public','reference','to_asap7']):
 z=comp[(comp.setting==d)&(comp.budget==4)].groupby(['family','method']).nrmse.mean().unstack();z.plot.bar(ax=ax,color=[colors[m] for m in z.columns],legend=False);ax.set(title=d,xlabel='',ylabel='Macro NRMSE',yscale='log');ax.tick_params(axis='x',rotation=45,labelsize=7)
fig.legend(*axs[0].get_legend_handles_labels(),loc='outside upper center',ncol=4,frameon=False);save(fig,'family_diagnostic')
(P/'INPUT_SHA256.json').write_text(json.dumps(inputs,indent=2))
print('derived files generated; input sources',len(inputs))
