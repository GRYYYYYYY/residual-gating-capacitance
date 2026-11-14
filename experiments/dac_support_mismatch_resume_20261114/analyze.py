"""Fixed paired aggregation and conditional group bootstrap; no new prediction."""
import json,csv,hashlib,time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from paths import *
from gates import endpoint_gate
endpoint_gate()
assert (OUT/'PIPELINE_SUCCESS.json').exists()
d=pd.read_csv(OUT/'EVALUATION_CELLS.csv',dtype={'arm':str})
assert len(d)==256*18*3 and d.status.eq('ok').all()
assert not d.duplicated(['cell','architecture','arm','train_seed','component_index']).any()
# Fail closed on incomplete or unequal populations, including zero-truth component sets.
for (a,p,s),x in d.groupby(['architecture','arm','train_seed']):assert len(x)==256*3
assert (d.groupby(['cell','component_index']).squared_truth.nunique()==1).all()
assert (d.groupby('cell').query_count.nunique()==1).all()
keys=['cohort','architecture','arm','train_seed','cell','table_id','group','process','family','budget','data_seed','protocol']
cells=d.groupby(keys,dropna=False).nrmse.mean().reset_index()
low=cells[cells.cohort=='low'];high=cells[cells.cohort=='high']
# Table/data seeds -> table -> dependency group. Low budgets stay separate until equal averaging.
lowtable=low.groupby(['architecture','arm','train_seed','table_id','group','process','family','budget']).nrmse.mean().reset_index()
hightable=high.groupby(['architecture','arm','train_seed','table_id','group','process','family']).nrmse.mean().reset_index();hightable['budget']='original_support'
table=pd.concat([lowtable.assign(cohort='low'),hightable.assign(cohort='high')],ignore_index=True)
table.to_csv(OUT/'TABLE_ERRORS.csv',index=False)
group=table.groupby(['cohort','architecture','arm','train_seed','group','process','budget']).nrmse.mean().reset_index()
# Supplement low group rows pooled by equal four-budget mean.
groupall=group[group.cohort=='low'].groupby(['cohort','architecture','arm','train_seed','group','process']).nrmse.mean().reset_index();groupall['budget']='ALL_4_EQUAL'
group=pd.concat([group,groupall],ignore_index=True);group.to_csv(OUT/'GROUP_ERRORS.csv',index=False)
errors=group.groupby(['cohort','budget','architecture','arm','train_seed']).nrmse.mean().reset_index();errors.to_csv(OUT/'ERRORS_BY_SEED_BUDGET.csv',index=False)

def effect(row):
 f0,fh,fl,b0,bh,bl=[float(row[a,p]) for a,p in [('Full','0'),('Full','H'),('Full','L'),('binary','0'),('binary','H'),('binary','L')]]
 return dict(E_Full_0=f0,E_Full_H=fh,E_Full_L=fl,E_binary_0=b0,E_binary_H=bh,E_binary_L=bl,C_Full=f0-fh,C_binary=b0-bh,D_Full=fh-fl,D_binary=bh-bl,I=(fh-fl)-(bh-bl),G=bl-fl)
wide=errors.pivot(index=['cohort','budget','train_seed'],columns=['architecture','arm'],values='nrmse');effectrows=[dict(cohort=k[0],budget=k[1],train_seed=k[2],**effect(row)) for k,row in wide.iterrows()];effects=pd.DataFrame(effectrows);effects.to_csv(OUT/'EFFECTS_BY_SEED_BUDGET.csv',index=False);primary=effects[(effects.cohort=='low')&(effects.budget=='ALL_4_EQUAL')];assert len(primary)==3;primary.to_csv(OUT/'EFFECTS_BY_SEED.csv',index=False)
for name,df,idx in [('EFFECTS_BY_TABLE.csv',table,['cohort','budget','train_seed','table_id','group','process','family']),('EFFECTS_BY_GROUP.csv',group,['cohort','budget','train_seed','group','process'])]:
 w=df.pivot(index=idx,columns=['architecture','arm'],values='nrmse');pd.DataFrame([dict(zip(idx,k),**effect(r)) for k,r in w.iterrows()]).to_csv(OUT/name,index=False)
# Component-specific counterparts, with identical equal weighting of tables/groups/budgets.
comp=d[d.cohort=='low'].groupby(['architecture','arm','train_seed','component','table_id','group','process','budget']).nrmse.mean().reset_index()
comp=comp.groupby(['architecture','arm','train_seed','component','group','process','budget']).nrmse.mean().reset_index().groupby(['architecture','arm','train_seed','component','budget']).nrmse.mean().reset_index()
w=comp.pivot(index=['component','budget','train_seed'],columns=['architecture','arm'],values='nrmse');pd.DataFrame([dict(component=k[0],budget=k[1],train_seed=k[2],**effect(r)) for k,r in w.iterrows()]).to_csv(OUT/'EFFECTS_BY_COMPONENT.csv',index=False)
# Historical pooled metric, separately named. Sum SSE/SY in process/family/component then sqrt.
pool=d.groupby(['cohort','budget','architecture','arm','train_seed','process','family','component_index'])[['squared_error','squared_truth']].sum().reset_index();pool['nrmse']=np.where(pool.squared_truth>0,np.sqrt(pool.squared_error/pool.squared_truth),np.nan);pool.groupby(['cohort','budget','architecture','arm','train_seed']).nrmse.mean().reset_index().to_csv(OUT/'OLD_E1_POOLED_BY_SEED.csv',index=False)
# Fixed-seed mean effect and paired dependency-group bootstrap, stratified by process.
ge=pd.read_csv(OUT/'EFFECTS_BY_GROUP.csv');ge=ge[(ge.cohort=='low')&(ge.budget.astype(str)=='ALL_4_EQUAL')]
metrics=['C_Full','C_binary','D_Full','D_binary','I','G'];gm=ge.groupby(['process','group'])[metrics].mean();assert len(gm)==4
rng=np.random.default_rng(61114);boot=[]
for _ in range(2000):
 samples=[]
 for process,g in gm.groupby(level='process'):
  ids=rng.integers(0,len(g),len(g));samples.extend(g.iloc[ids].values)
 boot.append(np.mean(samples,axis=0))
boot=np.asarray(boot);summary=[]
for i,m in enumerate(metrics):summary.append(dict(effect=m,mean=float(primary[m].mean()),seed_min=float(primary[m].min()),seed_max=float(primary[m].max()),positive_seeds=int((primary[m]>0).sum()),negative_seeds=int((primary[m]<0).sum()),zero_seeds=int((primary[m]==0).sum()),conditional_group_ci_low=float(np.quantile(boot[:,i],.025)),conditional_group_ci_high=float(np.quantile(boot[:,i],.975)),bootstrap_replicates=2000,dependency_groups=4,training_seeds=3))
pd.DataFrame(summary).to_csv(OUT/'EFFECT_SUMMARY.csv',index=False)
# Tails are paired cell/component values; they are not pooled quantiles or timing slack.
tail=d.groupby(['cohort','budget','architecture','arm','train_seed'])[['p95_absolute','p99_absolute']].mean().reset_index();tail.to_csv(OUT/'TAIL_ERROR_SUMMARY.csv',index=False)
lt=d[d.cohort=='low'];tw=lt.pivot(index=['cell','table_id','group','budget','data_seed','component','train_seed','unit'],columns=['architecture','arm'],values='p99_absolute');pd.DataFrame([dict(zip(['cell','table_id','group','budget','data_seed','component','train_seed','unit'],k),Full_L_minus_binary_L_p99=float(r['Full','L']-r['binary','L'])) for k,r in tw.iterrows()]).to_csv(OUT/'TAIL_PAIRED_DIFFERENCES.csv',index=False)
# Source continuation costs include pilot prefixes; startup/preflight accounted separately in ledger.
tr=[]
for unit in json.loads((OUT/'FROZEN_PLAN.yaml').read_text())['unit_order']:
 p=OUT/'checkpoints'/unit;r=json.loads((p/'COMPLETED.json').read_text());pilot=json.loads((p/'PILOT.json').read_text()) if (p/'PILOT.json').exists() else None
 tr.append(dict(unit=unit,architecture=r['architecture'],arm=r['arm'],seed=r['seed'],updates=r['updates'],pilot_updates=20 if pilot else 0,formal_startstep=r['startstep'],source_training_cpu_s=r['training_cpu_s']+(pilot['training_cpu_s'] if pilot else 0),source_training_wall_s=r['training_wall_s']+(pilot['training_wall_s'] if pilot else 0),checkpoint_path=str(p/'checkpoint.pt'),checkpoint_sha256=sha(p/'checkpoint.pt'),status='completed'))
pd.DataFrame(tr).to_csv(OUT/'ENDPOINT_COSTS.csv',index=False)
timing=pd.read_csv(OUT/'PREDICTION_TIMING.csv');timing['encoding_plus_forward_cpu_s']=timing.encoding_cpu_shared_per_arch_cell_s+timing.forward_cpu_s;timing.groupby(['cohort','budget','architecture','arm']).agg(forward_cpu_mean_s=('forward_cpu_s','mean'),forward_wall_mean_s=('forward_wall_s','mean'),one_model_completion_cpu_mean_s=('encoding_plus_forward_cpu_s','mean'),encoding_shared_cpu_mean_s=('encoding_cpu_shared_per_arch_cell_s','mean')).reset_index().to_csv(OUT/'PREDICTION_COST_SUMMARY.csv',index=False)
# Old MLP/CNP describe different training opportunity; recompute the SAME new primary from old fixed S/Q.
import gzip
oldpath=ROOT/'results/dac_characterization_20261114/confirmation_reference/records.jsonl.gz';old=[]
with gzip.open(oldpath,'rt') as f:
 for line in f:
  r=json.loads(line)
  if r['strategy']=='farthest' and r['budget'] in [4,8,16,32] and r['method'] in ['mlp_adapt','cnp','full','binary']:
   se=np.asarray(r['squared_error']);sy=np.asarray(r['squared_truth']);old.append(dict(method=r['method'],budget=r['budget'],table_id=r['table_id'],group=r['dependency_group'],data_seed=r['data_seed'],nrmse=float(np.sqrt(se[sy>0]/sy[sy>0]).mean()),status=r['status']))
old=pd.DataFrame(old);assert old.status.eq('ok').all();old=old.groupby(['method','budget','table_id','group']).nrmse.mean().reset_index().groupby(['method','budget','group']).nrmse.mean().reset_index().groupby(['method','budget']).nrmse.mean().reset_index();old['comparison']='historical ensemble / baseline; different source-training opportunity; descriptive only';old.to_csv(OUT/'HISTORICAL_DESCRIPTIVE.csv',index=False)
# Scientific plots from the exported summary tables, retain all three members.
fig,ax=plt.subplots(figsize=(6.8,4.3));colors={'Full':'#2166ac','binary':'#b2182b'};styles={'0':':','H':'--','L':'-'}
for (a,arm),g in errors[(errors.cohort=='low')&errors.budget.isin([4,8,16,32])].groupby(['architecture','arm']):
 for s,gs in g.groupby('train_seed'):ax.plot(gs.budget.astype(int),gs.nrmse,color=colors[a],ls=styles[arm],alpha=.18,lw=.8)
 gg=g.groupby('budget').nrmse.mean();ax.plot(gg.index.astype(int),gg.values,color=colors[a],ls=styles[arm],marker='o',label=f'{a}-{arm}')
ax.set(xlabel='Observed support B',ylabel='Query NRMSE (table/group primary)');ax.set_xticks([4,8,16,32]);ax.legend(ncol=2,fontsize=8);fig.tight_layout();fig.savefig(OUT/'error_budget.pdf');fig.savefig(OUT/'error_budget.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(6.8,4.3));x=np.arange(len(metrics))
for seed in range(3):ax.scatter(x+(seed-1)*.12,[primary[primary.train_seed==seed][m].iloc[0] for m in metrics],label=f'train seed {seed}',s=32)
means=np.array([r['mean'] for r in summary]);lo=np.array([r['conditional_group_ci_low'] for r in summary]);hi=np.array([r['conditional_group_ci_high'] for r in summary]);ax.errorbar(x,means,yerr=[means-lo,hi-means],fmt='k_',capsize=4,label='mean; paired group 95% interval')
ax.axhline(0,color='gray',lw=.8);ax.set_xticks(x,['C Full','C binary','D Full','D binary','I','G']);ax.set_ylabel('Paired NRMSE difference (positive = defined benefit)');ax.legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'paired_effects.pdf');fig.savefig(OUT/'paired_effects.png',dpi=180);plt.close(fig)
atomic_json(OUT/'ANALYSIS_SUCCESS.json',dict(status='success',attempt_id=ATTEMPT,analysis_code_sha256=sha(Path(__file__)),freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json'),evaluation_sha256=sha(OUT/'EVALUATION_CELLS.csv'),primary_aggregation='unchanged FROZEN_PLAN.metric',population_cells=256,component_rows=len(d),endpoints=12,means={m:float(primary[m].mean()) for m in metrics},bootstrap_caveat='conditional on 4 existing groups and fixed 3 training seeds; not independent ensembles'))
print(primary.to_string(index=False),flush=True);print(pd.DataFrame(summary).to_string(index=False),flush=True)
