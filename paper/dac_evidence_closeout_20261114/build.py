"""Editorial closeout: read archived CSVs only; no model imports or execution."""
from pathlib import Path
import csv,json,hashlib,re,subprocess,sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent;ROOT=P.parents[1];R=ROOT/'results/dac_support_mismatch_resume_20261114';S=ROOT/'results/dac_characterization_20261114/summary';V=ROOT/'review/dac_capacitance_20261114';OLD=ROOT/'paper/dac_mechanism_resume_20261114'
refs={}
def read(p):
 b=p.read_bytes();refs[str(p.relative_to(ROOT))]=hashlib.sha256(b).hexdigest();return b.decode()
def frame(p):read(p);return pd.read_csv(p)
for p in [ROOT/'docs/dac_support_mismatch_resume_20261114'/n for n in ['MECHANISM_REPORT.md','REPRODUCE.md','CLAIM_EVIDENCE.csv']]+[V/'REVIEW_PACKET.md',OLD/'SOURCE_OF_TRUTH.md',OLD/'main.tex']:read(p)
inputs={n:frame(R/(n+'.csv')) for n in ['EFFECTS_BY_SEED','EFFECTS_BY_SEED_BUDGET','PREDICTION_COST_SUMMARY','ENDPOINT_COSTS','HISTORICAL_DESCRIPTIVE','OLD_E1_POOLED_BY_SEED','TAIL_ERROR_SUMMARY','TAIL_PAIRED_DIFFERENCES']}
deltas=frame(V/'downstream_deltas.csv');ds=frame(V/'downstream_delta_summary.csv');raw=frame(S/'downstream_raw.csv');oldmeans=frame(S/'downstream_means.csv')
for p in [ROOT/'pdkcap/metrics.py',ROOT/'experiments/dac_characterization_20261114/summarize_downstream.py',ROOT/'experiments/dac_characterization_20261114/evaluate.py']:read(p)
old=read(OLD/'DAC_REWRITE.md')
def save(name,df):df.to_csv(P/(name+'.csv'),index=False)
def table(df,digits=6):
 vals=[]
 for row in df.itertuples(index=False,name=None):vals.append('| '+' | '.join(f'{x:.{digits}f}' if isinstance(x,(float,np.floating)) else str(x) for x in row)+' |')
 return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join(vals)+'\n'
e=inputs['EFFECTS_BY_SEED_BUDGET'];low=e[e.cohort=='low'];mean=low.groupby('budget').mean(numeric_only=True).drop(columns='train_seed').reindex(['4','8','16','32','ALL_4_EQUAL']);assert len(mean)==5
mt=mean[['E_Full_0','E_Full_H','E_Full_L','E_binary_L','G']].reset_index();mt.columns=['B','Full-0','Full-H','Full-L','binary-L','G'];mt['B']=mt.B.replace({'ALL_4_EQUAL':'Equal-budget mean'});save('mechanism_budget',mt)
ret=e[e.cohort=='high'].mean(numeric_only=True);retention=pd.DataFrame([{'Model':a,'0':ret['E_'+a+'_0'],'H':ret['E_'+a+'_H'],'L':ret['E_'+a+'_L']} for a in ['Full','binary']]);save('retention',retention)
t=inputs['PREDICTION_COST_SUMMARY'];cost=t[(t.cohort=='low')&(t.arm=='L')].pivot(index='budget',columns='architecture',values='one_model_completion_cpu_mean_s')*1000;cost['Full/binary']=cost.Full/cost.binary;save('completion_cost_ms',cost.reset_index())
cpu=inputs['ENDPOINT_COSTS'];cpu=cpu[cpu.arm=='L'].groupby('architecture').source_training_cpu_s.sum();save('source_continuation_cost',cpu.rename('CPU_seconds').reset_index())
tail=inputs['TAIL_PAIRED_DIFFERENCES'].Full_L_minus_binary_L_p99;counts=[int((tail<0).sum()),int((tail==0).sum()),int((tail>0).sum())];assert counts==[887,225,616]
# Same native batch; first average data seeds within each fixed layout and budget.
metrics=['net_cap_nrmse','ws_abs_ns','slack_p99_ns'];num=raw.select_dtypes('number').columns.difference(['budget','data_seed']);native=raw.groupby(['case','method','budget'])[num].mean().reset_index()
for c in metrics:
 merged=native.merge(oldmeans,on=['case','method','budget'],suffixes=('_new','_old'));assert np.allclose(merged[c+'_new'],merged[c+'_old'],rtol=1e-12,atol=1e-15)
full=native[native.method=='full'].set_index(['case','budget']);binary=native[native.method=='binary'].set_index(['case','budget']);diff=full[metrics]-binary[metrics];assert (diff.slack_p99_ns>0).sum()==10
worst=diff.slack_p99_ns.idxmax();worstps=1000*diff.slack_p99_ns.max();assert worst==('gf180/ibex',4) and abs(worstps-7.643287)<1e-5
for m in metrics:
 r=ds[(ds.comparator=='binary')&(ds.metric==m)].iloc[0];assert abs(diff[m].max()-r.max_signed_difference)<1e-12
n=native[native.method.isin(['cmi','binary','full'])].copy();n['cap_unit']=n['case'].map(raw.groupby('case').cap_unit.first());save('native_all_layouts_all_metrics',n)
compact=n.groupby(['budget','method'])[metrics].mean().reset_index();compact['ws_abs_ns']*=1000;compact['slack_p99_ns']*=1000;compact.columns=['B','Method','Net C NRMSE','WS abs error ps','Mean per-layout P99 error ps'];save('native_compact',compact)
save('native_paired_deltas',diff.reset_index());save('native_delta_summary',ds[ds.comparator.isin(['cmi','binary'])])
# Check all mean-seed delta rows against the same original batch.
meanrows=deltas[deltas.data_seed.astype(str).str.contains('mean')]
for _,r in meanrows[meanrows.metric.isin(metrics)].iterrows():
 a=native[(native.case==r['case'])&(native.budget==r.budget)&(native.method=='full')].iloc[0];b=native[(native.case==r['case'])&(native.budget==r.budget)&(native.method==r.comparator)].iloc[0];assert abs((a[r.metric]-b[r.metric])-r.full_minus_comparator)<1e-12
# Figures are regenerated from existing summary values; no new model timing.
fig,ax=plt.subplots(figsize=(6.4,3.7))
for col in ['Full-0','Full-H','Full-L','binary-L']:ax.plot([4,8,16,32],mt.iloc[:4][col],marker='o',label=col)
ax.set(xlabel='Observed geometry budget B',ylabel='M: mean member query NRMSE');ax.set_xticks([4,8,16,32]);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(P/'figures/mechanism_budget.pdf');fig.savefig(P/'figures/mechanism_budget.png',dpi=160);plt.close(fig)
# Reuse verified explanatory prose and old E1 results; give each metric its own name.
def section(start,end):return old.split(start,1)[1].split(end,1)[0].strip()
related=section('## 2. Related work and comparison scope','## 3. Problem and extraction interface')
problem=section('## 3. Problem and extraction interface','## 4. Method and alternatives')
method=section('## 4. Method and alternatives','## 5. Experimental protocol and cost accounting')
protocol=section('## 5. Experimental protocol and cost accounting','## 6. Results')
rq1=section('### 6.1 Fixed-budget completion','### 6.4 Native extraction and STA')
# Keep E1 tables together and explicitly label their ensemble/pooled metric.
rq1=rq1.replace('### 6.2 Threshold attainment and characterization work','### Threshold attainment and cost stages').replace('### 6.3 Same-budget adaptation and related-work control','### Target adaptation and related-work control').replace('new completion wall seconds','archived completion wall seconds').replace('new completion/target','archived completion/target')
mechanism=section('## Matched support-protocol continuation','## 7. Limitations and conclusion')
mechanism=mechanism[:mechanism.index('Let C=')] # retain exact design and aggregation; replace overloaded results prose.
reference=old.split('## References',1)[1].strip()
relative=100*mean.loc['ALL_4_EQUAL','G']/mean.loc['ALL_4_EQUAL','E_binary_L'];gap0=mean.loc['ALL_4_EQUAL','E_binary_0']-mean.loc['ALL_4_EQUAL','E_Full_0'];shrink=100*(1-mean.loc['ALL_4_EQUAL','G']/gap0)
rises=[100*(mean.loc[b,'E_Full_L']/mean.loc[b,base]-1) for b in ['16','32'] for base in ['E_Full_0','E_Full_H']]
body=f'''# Sparse Capacitance Rule Completion: Support Protocols, Model Complexity, and Extraction Fidelity

## Abstract

Completing a capacitance rule library from sparse target-process observations is distinct from applying an extractor to a routed layout. We compare numerical completion, frozen support-conditioned predictors and target adaptation under common observation budgets, and export completed rules into an unchanged extraction and timing flow. Target adaptation and simple gates remain competitive alternatives to full numerical-neural fusion. In a matched FEM continuation, low-support training benefits binary gating more strongly; full fusion retains a small advantage under the prespecified four-budget average, while binary is more accurate at the smallest budget. Improvements at small budgets coexist with degradation at larger budgets and under the original support protocol. Fixed-layout extraction shows substantial gains over interpolation but mixed increments over binary gating, including timing-tail regressions. The evidence establishes budget- and protocol-dependent rankings in the evaluated cohorts, rather than general characterization savings or signoff accuracy.

## Introduction and research questions

An existing geometry-to-capacitance rule library can support offline completion without replacing the parasitic extractor. The engineering decision involves the observation budget, source training, target fitting and completion computation, followed by error propagation through a fixed downstream flow. We organize the evidence around three questions.

**RQ1:** How do numerical completion, frozen conditional prediction and target adaptation compare at the same target observation budget? **RQ2:** How does the training support protocol interact with model complexity and change these rankings? **RQ3:** How do completed-rule errors propagate to net capacitance and static timing in a fixed extraction flow?

The concrete contributions are an information-budget protocol with sealed queries and separate cost stages; a matched continuation showing budget-dependent support-protocol and complexity tradeoffs; and a native rule-export interface with paired extraction/timing error evidence. These are testable artifacts and empirical observations, not a claim that changing the paper's positioning establishes algorithmic novelty.

## Related work

{related}

## Rule-completion interface and models

{problem}

{method}

## Evaluation populations, metrics and costs

{protocol}

We distinguish **E1**, the historical process/family/component pooled query NRMSE computed after averaging predictions of the three trained members, from **M**, the mechanism metric computed separately for each member and then averaged over members. M averages nonzero-truth component NRMSE within table/data-seed/budget, then data seeds, tables within process-layer groups, groups and the four budgets equally. Pooling squared errors, averaging errors, and averaging predictions do not commute. E1 and M values are never subtracted from one another. OLD_E1_POOLED_BY_SEED reconstructs E1-style pooling for individual members; it does not turn them into an ensemble.

Source training, purchased target observations, target adaptation, rule completion and native extraction/STA are separate cost stages. Historical adaptation-plus-completion times remain combined; pure adaptation latency cannot be inferred. All findings below reuse completed records; this closeout adds no predictions or timing measurements.

## RQ1: Same-observation rule completion

All relative-error tables in this section use E1; trained predictors use their archived three-member ensemble, not the mean of three member errors. They compare the same S/Q and target observation budget, while source-training opportunities differ as specified above.

{rq1}

The first measured attainment budget is not the lowest necessary number of observations. Full, binary and adapted MLP all attain the frozen middle FEM/transfer thresholds at B4; no observation below B4 was tested. These are retrospective query-truth statistics, not an operational online stopping rule.

## RQ2: Support protocol and model complexity

{mechanism}

The following table uses M, averaged over the three individual training-seed errors. Its last row preserves the prespecified equal weighting of B4/B8/B16/B32. It is neither an ensemble error nor an E1 pooled score.

{table(mt)}

![M across budgets, from the same archived member results; original Full remains an explicit reference.](figures/mechanism_budget.pdf)

Full-L has {relative:.2f}% lower four-budget mean NRMSE than binary-L, with positive G in all three seeds. This is a relative change of these mean NRMSE values, not MAPE or a {relative:.2f}% reduction of every capacitance error. The original Full-0/binary-0 gap is {gap0:.6f}; after L it is {mean.loc['ALL_4_EQUAL','G']:.6f}, a {shrink:.1f}% narrowing. Low-support continuation did not create Full's average advantage.

At B4, binary-L is more accurate in all three seeds. At B8 it is better in two seeds and slightly worse in one, while its mean is lower. At B16/B32, Full-L outperforms binary-L but is worse than both Full-0 and Full-H: increases relative to Full-0 are {rises[0]:.2f}%/{rises[2]:.2f}%, and relative to Full-H {rises[1]:.2f}%/{rises[3]:.2f}%. These rank changes do not validate a post-hoc deployment policy choosing binary-L at small B and old Full at large B; no independent policy-selection evidence exists.

Define C[a]=E[a,0]-E[a,H], D[a]=E[a,H]-E[a,L], I=D[Full]-D[binary] and G=E[binary,L]-E[Full,L], all in M units. The paired seed effects are:

{table(inputs['EFFECTS_BY_SEED'][['train_seed','C_Full','C_binary','D_Full','D_binary','I','G']])}

Mean D[Full]=0.005066 is positive in two seeds, D[binary]=0.015766 in all three; I=-0.010701 is negative in all three. Binary thus responds more strongly. G=0.002939 is positive in all three, with a conditional group-bootstrap interval [0.000372,0.005507]. Four existing dependency groups and three fixed training seeds do not support population-wide process guarantees. This is a retrospective diagnosis; the confirmation cohort was already used to identify the question. Nested thinning changes both support count and coverage, not cardinality alone.

### Retention and computation

The same group/table weighting applied to64 original-protocol units yields the following member means. Low-support training is not a uniform improvement over H or over the starting models.

{table(retention)}

The next table reports archived shared-encoding CPU plus one member forward, in milliseconds. It is an estimated single-member completion cost, not measured ensemble wall latency and not OpenRCX/STA runtime.

{table(cost.reset_index().rename(columns={'budget':'B','Full':'Full-L ms','binary':'binary-L ms'}),2)}

Full-L costs {cost['Full/binary'].min():.2f}–{cost['Full/binary'].max():.2f} times binary-L here. Actual evaluation reused encoding across nine versions per architecture/cell; multiplying that shared cost by all versions would overcount measured work. Three-member computation would be shared encoding plus three forwards, not these single-member numbers. L source continuation costs {cpu['Full']:.2f} CPU seconds for Full and {cpu['binary']:.2f} for binary across their three seeds; these are incremental costs, not full training lifecycle totals. B4/B8 mean error and computation both favor binary-L, whereas B16/B32 compare a more accurate, more expensive Full-L against binary-L; old Full remains a better error reference at those larger budgets. No same-factor characterization or extraction speedup follows.

In1728 paired cell/component/seed P99 absolute capacitance-error comparisons, Full-L is lower in887, exactly tied in225 and higher in616. These correlated comparisons are not independent designs, globally pooled P99, or STA slack. All signed differences and original-support tails remain available in the referenced archives. Historical MLP/CNP recomputed under M are descriptive only: training opportunities, target adaptation and model aggregation differ from this matched experiment.

## RQ3: Native extraction and STA error propagation

The native study uses eight fixed layouts, B4/B8 and three data seeds, with83 eligible held-out rule tables replaced and all other rules kept complete. The original84-table set excludes one two-node ASAP7 OVER table under the common n<4 feasibility rule for every method; it remains golden. Golden means extraction using the full rules with the same ODB, SDC, Liberty and tool configuration. All240 candidate native runs and eight golden replays completed; net C/R golden replay agrees and candidate R is unchanged. These are archived original models, not the H/L continuation endpoints.

For compactness, the table first averages the three data seeds within each layout/budget, then equally averages eight layouts per budget. WS is the absolute deviation of worst slack from the golden reference. P99 is the99th percentile of absolute endpoint slack errors within each run, subsequently averaged; it is not a pooled endpoint percentile. Timing errors are converted from ns to ps. Individual layout values and all other metrics are in native_all_layouts_all_metrics.csv.

{table(compact,6)}

Across the16 layout/budget conditions (each a three-data-seed mean), Full improves net-C NRMSE and absolute WS error over CMI in16/16 conditions. Relative to binary, net-C improves/ties/worsens in6/0/10, WS in4/0/12, and P99 slack error in6/0/10. The largest P99 degradation is {worstps:.6f} ps at GF180/ibex B4: Full's P99 absolute error minus binary's, averaged over the same seeds. It is an error increase relative to the golden reference, not a loss of actual chip slack.

Tails and decisions do not all improve with net-C error. Against binary, TNS absolute error improves/ties/worsens in5/4/7, false negatives tie in16/16, and false positives tie/worsen in14/2. Against CMI, TNS counts are13/3/0, while false positives improve/tie/worsen in4/9/3. native_delta_summary.csv retains all19 reviewed metrics for both comparisons, including path/endpoint overlap and ranking. Numerical ties follow the existing tolerance max(1e-12,1e-9 times the larger magnitude); it is not an engineering-equivalence threshold. Shared libraries and layouts make the16 conditions dependent, not16 independent technologies.

## Limitations and conclusion

Public geometry is rank one; FEM is idealized two-dimensional electrostatics. Native evaluation replaces selected held-out rules, not an entirely sparse-characterized PDK. Physical accuracy, unseen processes, whole-process cost, true solver wall savings and signoff correctness are not established. The two-stack transfer and adapted AttentionCap results are unchanged; this mechanism study neither repairs their failure boundaries nor measures new downstream behavior. No endpoint-selection or budget-dependent router is validated by these retrospective rankings.

The evaluated rule-completion interface improves extraction fidelity in several fixed-observation settings, while target adaptation and simple residual gates remain competitive alternatives. In matched FEM continuation, low-support training benefits binary gating more than full numerical-neural fusion. Full retains a small advantage under the prespecified four-budget average, whereas binary is more accurate at the smallest budget. Low-support training also degrades larger-support conditions. These observations establish protocol- and budget-dependent rankings within this cohort, not universal architectural superiority or whole-process characterization savings.

## Artifact availability

The research branch contains evaluation scripts, CSVs, source manifests and editable manuscripts. Large checkpoint and dataset references include local paths and hashes; a hash or a successful local run does not establish publicly downloadable weights or a complete external reproduction environment. We make no claim that all underlying artifacts are openly available. This paper's small derived tables, figure and renderer are packaged; the historical archives are referenced rather than duplicated. No new data or weight publication is performed.

## References

{reference}
'''
body=re.sub(r'(?<=[A-Za-z])(?=\d)', ' ',body) if False else body
# Fix only prose spacing, never scientific values or symbols.
for a,b in [('to64','to 64'),('In1728','In 1728'),('in887','in 887'),('in225','in 225'),('in616','in 616'),('with83','with 83'),('original84','original 84'),('All240','All 240'),('the99th','the 99th'),('the16','the 16'),('in16/16','in 16/16'),('in6/0/10','in 6/0/10'),('in4/0/12','in 4/0/12'),('in5/4/7','in 5/4/7'),('in14/2','in 14/2'),('are13/3/0','are 13/3/0'),('in4/9/3','in 4/9/3'),('all19','all 19'),('not16','not 16')]:body=body.replace(a,b)
body='\n'.join(x.rstrip() for x in body.splitlines())+'\n';(P/'DAC_REWRITE.md').write_text(body)
(P/'INPUT_SHA256.json').write_text(json.dumps(refs,indent=2))
(P/'CHECKS.json').write_text(json.dumps(dict(start_sha='dce58bed002dd7440f963bcb21f28859bfcc6973',new_training=0,new_predictions=0,new_model_timing=0,new_solver_transfer_STA=0,mechanism_rows=len(e),tail_counts=counts,native_raw_rows=len(raw),native_means_match=True,p99_worst_case=[worst[0],int(worst[1])],p99_worst_delta_ps=worstps,relative_average_gain_percent=relative,gap_shrink_percent=shrink,Full_L_increase_percent_B16_vs0_vsH_B32_vs0_vsH=rises,input_files=len(refs)),indent=2))
print((P/'CHECKS.json').read_text())
