"""One final paper revision after all fixed scientific results exist."""
import json,csv,shutil,subprocess,re,sys
from pathlib import Path
import pandas as pd
from paths import *
assert (OUT/'ANALYSIS_SUCCESS.json').exists()
PAPER=ROOT/'paper/dac_mechanism_resume_20261114';PAPER.mkdir(exist_ok=False)
oldpaper=ROOT/'paper/dac_revision_20261114'
shutil.copytree(oldpaper/'figures',PAPER/'figures')
for name in ['error_budget.pdf','paired_effects.pdf']:shutil.copyfile(OUT/name,PAPER/'figures'/name)
effects=pd.read_csv(OUT/'EFFECTS_BY_SEED.csv');summary=pd.read_csv(OUT/'EFFECT_SUMMARY.csv');err=pd.read_csv(OUT/'ERRORS_BY_SEED_BUDGET.csv',dtype={'arm':str,'budget':str});cost=pd.read_csv(OUT/'ENDPOINT_COSTS.csv');tails=pd.read_csv(OUT/'TAIL_PAIRED_DIFFERENCES.csv');high=pd.read_csv(OUT/'EFFECTS_BY_SEED_BUDGET.csv',dtype={'budget':str});high=high[high.cohort=='high']
means=effects.select_dtypes('number').mean().to_dict();f=lambda x:f'{float(x):.6f}'
all_effects=pd.read_csv(OUT/'EFFECTS_BY_SEED_BUDGET.csv',dtype={'budget':str})
budget_means=all_effects[(all_effects.cohort=='low')&(all_effects.budget!='ALL_4_EQUAL')].groupby('budget').mean(numeric_only=True).drop(columns='train_seed').reindex(['4','8','16','32'])
budget_means.to_csv(OUT/'BUDGET_MEAN_EFFECTS.csv')

status='LOW_SUPPORT_PROTOCOL_EFFECT_OBSERVED' if (effects.D_Full>0).all() and (effects.D_binary>0).all() else 'LIMITED_OR_INCONSISTENT_PROTOCOL_EFFECT'
local='LOCAL_FULL_ADVANTAGE_OBSERVED' if (effects.G>0).all() else ('FULL_NOT_BETTER_AFTER_MATCHED_LOW_SUPPORT' if (effects.G<0).all() else 'FULL_ADVANTAGE_NOT_SEED_STABLE')
def mdtable(df):
 cols=list(df.columns);rows=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
 for vals in df.itertuples(index=False,name=None):rows.append('| '+' | '.join(f(x) if isinstance(x,float) else str(x) for x in vals)+' |')
 return '\n'.join(rows)
last=json.loads((OUT/'ANALYSIS_SUCCESS.json').read_text());feas=json.loads((OUT/'FEASIBILITY.json').read_text())
seedtable=mdtable(effects[['train_seed','E_Full_0','E_Full_H','E_Full_L','E_binary_0','E_binary_H','E_binary_L','C_Full','C_binary','D_Full','D_binary','I','G']])
intervaltable=mdtable(summary[['effect','mean','seed_min','seed_max','positive_seeds','conditional_group_ci_low','conditional_group_ci_high']])
(DOC/'MECHANISM_REPORT.md').write_text(f'''# 原定支持协议匹配验证：完成报告

**机制状态：{status}；局部架构状态：{local}。全局仍为 COMPLETION_ACCURACY_ONLY。**

实际起点 `449fa39556ef9803d8e5eda14ec330324cb3383b`，原研究分支；旧失败、旧论文和原始结果均保留。新 attempt 是原14,400 CPU秒预算的接续，不是新预算。工程修复和历史失败记录见 REPAIR_AND_RESUME.md；阶段回执、冻结清单及账本位于 results/dac_support_mismatch_resume_20261114/。

## 完成状态

真实回归、prepare、freeze成功；seed0四个20步pilot成功，可行性保守估算{feas['estimated_total_cpu_s']:.3f} CPU秒，含原扣账、2倍最慢pilot速率、1800秒预测/统计/退出预留。正式对照计划12、启动12、完成12、训练失败0、未启动0，每成员精确2000步。seed0从完整pilot模型/optimizer/RNG/step20续训1980步，其余从step0训练2000步；没有额外20步或挑选中途checkpoint。

评估256单元（192低预算、64原支持）×18模型版本（6原始成员+12终点）×3分量=13,824行。所有方法共同S/Q、同尺度、只算Q；失败0。真实载入训练/确认表内容与冻结哈希相同。六个source权重及十二个终点路径/哈希在lineage与ENDPOINT_COSTS中，不能把三个seed称为三个独立ensemble。

## 主指标与连续效应

每表/数据seed/预算，先平均非零真值分量的sqrt(SSE/SY)；再平均数据seed、同process-layer内各表、各组，最后四预算等权。未把支持点零误差计入。4个依赖组、16张确认表、3个数据seed和3个训练seed均完整保留。原E1按process/family/component先池化SSE/SY后开方，另见 OLD_E1_POOLED_BY_SEED.csv，不能与此主指标混为一谈。

C[a]=E[a,0]−E[a,H]；D[a]=E[a,H]−E[a,L]；I=D[Full]−D[binary]；G=E[binary,L]−E[Full,L]。正D表示低支持协议的额外改善，正G才是Full-L绝对误差较小；正I不能替代G。

{seedtable}

三seed平均 D[Full]={f(means['D_Full'])}、D[binary]={f(means['D_binary'])}、I={f(means['I'])}、G={f(means['G'])}。所有seed及逐预算在 EFFECTS_BY_SEED_BUDGET.csv；分量、各表、依赖组的配对差异分别完整导出。主结果不以B4单点替代四预算平均。

{intervaltable}

区间是按process分层、组内保留方法/预算/轨迹/三个固定训练seed配对的2000次bootstrap，RNG61114；仅4个既有依赖组。它们对当前已知数据和三个固定训练重复有条件性，不能视作跨工艺总体区间，不能把query或预算点当独立样本。

## 预算分解：不能把四预算平均胜出解读为最低预算优势

{mdtable(budget_means[['D_Full','D_binary','I','G']].reset_index())}

B4上，Full-L对binary-L的G在三个seed均为负，均值{f(budget_means.loc['4','G'])}；四预算平均G为正，来自较高预算的优势，不能推广到每个预算。Full在B16、B32的D均在三个seed为负；binary在B32的D也均为负。均值B32 D[Full]={f(budget_means.loc['32','D_Full'])}、D[binary]={f(budget_means.loc['32','D_binary'])}。低支持训练帮助最小预算，但存在预算间取舍。

原始权重的四预算平均binary-minus-Full差值为{f(means['E_binary_0']-means['E_Full_0'])}，续训L后缩小至{f(means['G'])}。因此本轮的低支持协议没有创造Full的平均优势；binary响应更强，I在三个seed均为负。此局部平均差值不足以证明复杂门控必要性，完成本次诊断后停止Full进一步扩展。

## 遗忘、尾部与计算代价

原支持检查沿用同16确认表、四原协议、缺失率.3和数据seed11；主组/表权重不变。以下是原支持下的C/D/I/G，与低预算结果分开解释（正D表示L在原支持下也比H误差小；负D表示相对H遗忘）。

{mdtable(high[['train_seed','E_Full_0','E_Full_H','E_Full_L','E_binary_0','E_binary_H','E_binary_L','D_Full','D_binary','G']])}

低预算逐cell/component/训练seed的P99绝对电容误差比较，Full-L较binary-L更低{int((tails.Full_L_minus_binary_L_p99<0).sum())}项、精确平局{int((tails.Full_L_minus_binary_L_p99==0).sum())}项、更高{int((tails.Full_L_minus_binary_L_p99>0).sum())}项，最大差值{tails.Full_L_minus_binary_L_p99.max():.9g} F/m。它们是相关细分单元的描述性计数；平均单元P99不是全局池化P99，也不是STA slack。全部分量/表尾部保留，未只展示胜出数量。

十二成员纯source续训CPU（含pilot前缀）合计{cost.source_training_cpu_s.sum():.3f}秒；source训练不能视为免费。ENDPOINT_COSTS分列各条件，RESOURCE_LEDGER还计入载入、预检、失败、统计和监督开销。PREDICTION_COST_SUMMARY分别记录forward、共享encoding及单成员补表CPU估计，encoding每架构/cell只执行一次并被9个模型版本复用，不能按9倍计入实际总CPU。训练更新数相同不意味着Full/binary耗时相同。三个成员ensemble需共享encoding加三次forward，表中单成员延迟不能当ensemble延迟。

## 解释边界与研究决策

本次检验的是嵌套低支持协议：S_L⊆S_H，但数量和几何覆盖一起改变。H恢复原sampler分布，并按冻结seed重新开始其episode流；它不是恢复历史optimizer/RNG轨迹后的第12001步。已知153节点训练支持46/77/107/138或整宽136，与B4/8/16/32存在设置失配；匹配更新的D将该协议效应与单纯额外训练的C区分，但不证明纯数量因果机制。

{'Full和binary的D均在三个seed为正，支持此FEM回顾性范围内低支持协议有额外收益；这不是Full独有机制。' if status=='LOW_SUPPORT_PROTOCOL_EFFECT_OBSERVED' else '至少一个架构的D未在三个seed稳定为正；只按连续效应与区间陈述，不扩大为稳定机制。'} {'Full-L的G在三个seed均为正，给出当前FEM设置内的局部架构线索；仍须结合尾部、原支持退化和计算成本。' if local=='LOCAL_FULL_ADVANTAGE_OBSERVED' else 'Full-L未在三个seed稳定优于binary-L；改善幅度或正I不能证明Full的实际必要性。'}

旧MLP/CNP等在相同固定S/Q上的新主指标描述性重算见 HISTORICAL_DESCRIPTIVE.csv；它们没有获得本次匹配续训机会，不能据此声称公平训练优越。原始旧E1三成员均值与当前逐成员均值也有非线性聚合差异。没有重训任何这些基线。

保持限定规则补全主张；不升级普遍复杂门控必要性、全工艺表征效率、真实场求解加速、跨工艺总体或签核准确性。0.2882/0.2908阈值与B4首次已测下限结论不变；没有B1–3、没有新工程容差。原迁移、native PEX/STA及特定条件下Full相对binary的约+7.64 ps P99 slack误差差异没有重测，不据本机制实验宣称修复。本轮完成即停止，不追加搜索、模型、工艺或下游实验。{'可以保留局部机制结果；若未来另行研究，仍缺独立工艺/部署证据和工程收益阈值，本轮不自动获取。' if local=='LOCAL_FULL_ADVANTAGE_OBSERVED' else '现有结果不足以支持继续Full复杂化，维持结束Full扩展的建议。'}

## 论文与复现

paper/dac_mechanism_resume_20261114/DAC_REWRITE.md 是唯一正文主源，render_paper.py生成main.tex；main.pdf由两遍pdflatex生成。机制节位于局限之前，References最后。开发管理表述移至本报告/REPAIR_AND_RESUME和账本，原科学反例保留。原两版论文保持原样。轻量审阅包含报告、计划、小表、图和新论文；大权重/raw预测用路径和哈希引用。最终累计费用另见RESOURCE_SUMMARY.json及交付计量段。
''')
(DOC/'FINAL_DECISION.md').write_text(f'''# Decision

Global: **COMPLETION_ACCURACY_ONLY** (unchanged).
Mechanism: **{status}**.
Local architecture: **{local}**.

All12 fixed2000-update endpoints and all256 evaluation cells completed. Mean D Full={f(means['D_Full'])}, D binary={f(means['D_binary'])}, I={f(means['I'])}, G={f(means['G'])}. See all three seeds, conditional group intervals, forgetting and tail tradeoffs in MECHANISM_REPORT.md. No new transfer/solver/native STA evidence. Stop the bounded study; no automatic follow-up.
''')
# Use old authoritative Markdown, remove administrative prose, and integrate the final mechanism before limitations.
body=(oldpaper/'DAC_REWRITE.md').read_text();body=re.sub(r'^Research revision for a DAC-oriented evaluation\..*\n','',body,flags=re.M)
body=re.sub(r' One new public execution attempt stalled.*?Neither administrative event is hidden as successful scientific evidence\.','',body,flags=re.S)
body=body.replace('We therefore retain the conservative rule-completion title and stop with COMPLETION_ACCURACY_ONLY. The evidence does not support the broader characterization-efficiency repositioning or justify an immediate submission on that claim. Further work would require a separately registered application threshold, stronger independent physical/deployment evidence and a clearly isolated contribution; it is not automatically launched in this study.','The results support bounded rule completion rather than a general characterization-efficiency advantage. Independent physical and deployment evidence, together with an application-derived error requirement, would be needed to establish broader engineering value.')
body=body.replace('Detailed full-text methodological claims were not independently reverified in this run.','')
body=body.replace('On finite-element and FreePDK15-to-ASAP7 cohorts, target-adapted direct regression','For the archived models on finite-element and FreePDK15-to-ASAP7 cohorts, target-adapted direct regression')
abstract=f' A matched source-continuation study on the existing FEM cohort yields mean low-support protocol effects of {f(means["D_Full"])} for Full and {f(means["D_binary"])} for binary, with a final binary-minus-Full error gap of {f(means["G"])} under a separately specified table/group metric. These retrospective effects do not establish cross-process or downstream benefits.'
body=body.replace('but not a general characterization-cost advantage or universal necessity of complex gating.','but not a general characterization-cost advantage or universal necessity of complex gating.'+abstract,1)
newsection=f'''## Matched support-protocol continuation

The archived FEM models were trained on16 tables with153 geometry nodes each. Original missing-point protocols expose46,77,107 or138 nodes; whole-width holdout exposes136. The budgets4,8,16 and32 are below that support-count range. We compare Full and binary under the original support protocol H and a nested low-support protocol L, with the same three starting seeds. Each member receives2000 additional AdamW updates (learning rate0.0002, weight decay0.0001, gradient clipping1), all parameters trainable, dropout0 and equally weighted four-family normalized Huber losses. Missing historical optimizer states are reset identically in both arms. L takes a geometry-only coverage prefix of4,8,16 or32 points from H; the table, full geometry, original loss queries, normalization and loss weights remain paired. Removed observations are not additional loss queries. This changes both support cardinality and coverage, so the contrast identifies a support-protocol effect rather than a pure cardinality effect.

We evaluate all12 fixed endpoints and the six starting members on the same192 low-budget cells, plus64 original-support cells for retention. The primary mechanism metric averages component query NRMSE within each table/data seed/budget, then data seeds, tables within process-layer groups, groups, and finally the four budgets equally. This differs from the earlier tables' process/family/component pooled SSE/SY metric. The16 confirmation tables and four dependency groups have been used previously; this is a retrospective diagnosis. Three training seeds are paired repeats, not three independent ensembles.

Let C=E0-EH denote continued-original-protocol improvement, D=EH-EL the additional low-support-protocol effect, I=D(Full)-D(binary) the differential response and G=E(binary,L)-E(Full,L) the final architecture gap. Positive I does not imply positive G.

{mdtable(effects[['train_seed','C_Full','C_binary','D_Full','D_binary','I','G']])}

Mean D(Full)={f(means['D_Full'])}, D(binary)={f(means['D_binary'])}, I={f(means['I'])} and G={f(means['G'])}. {'Both architectures improve under L relative to matched-update H in all three seeds, indicating a shared low-support-protocol benefit.' if status=='LOW_SUPPORT_PROTOCOL_EFFECT_OBSERVED' else 'The sign pattern is not consistent across all architecture/seed contrasts, limiting a stable protocol-effect interpretation.'} {'Full-L has lower primary error than binary-L for all three seeds in this cohort.' if local=='LOCAL_FULL_ADVANTAGE_OBSERVED' else 'Full-L does not have consistently lower primary error than binary-L across the three seeds; a larger protocol response cannot establish its necessity.'} The paired, process-stratified group-bootstrap95% interval for G is [{f(summary[summary.effect=='G'].iloc[0].conditional_group_ci_low)},{f(summary[summary.effect=='G'].iloc[0].conditional_group_ci_high)}], conditional on four existing groups and the three fixed training seeds.

The budget-wise contrasts expose a tradeoff hidden by the four-budget average. At B4, G is negative in all three seeds, with mean{f(budget_means.loc['4','G'])}: binary-L has lower error than Full-L. Full's D is negative for all three seeds at both B16 and B32, and binary's D is negative for all three seeds at B32. At B32, mean D(Full)={f(budget_means.loc['32','D_Full'])} and D(binary)={f(budget_means.loc['32','D_binary'])}. The archived starting members already favor Full on the four-budget mean, with a binary-minus-Full gap of{f(means['E_binary_0']-means['E_Full_0'])}; the gap narrows after L. Binary therefore benefits more from the protocol change in every seed, rather than exposing a Full-specific mechanism.

Under the original-support retention check, mean D(Full)={f(high.D_Full.mean())} and D(binary)={f(high.D_binary.mean())}; negative D indicates worse L error than matched H in that regime. Across low-budget cell/component/seed comparisons, Full-L has higher P99 absolute capacitance error than binary-L in{int((tails.Full_L_minus_binary_L_p99>0).sum())} of{len(tails)} correlated cells. These tail summaries do not measure timing slack. Source continuation consumes{cost.source_training_cpu_s.sum():.2f} CPU seconds across all12 members, including the pilot prefixes; full preparation and evaluation accounting is reported separately. Historical MLP/CNP results have different training opportunities and serve only as descriptive references.

No new field solves, target training labels, transfer training or native extraction/STA runs are included in this continuation. Local FEM effects therefore do not resolve the existing downstream tail-error counterexample or establish whole-process characterization savings.

'''
# Typographic spacing in generated prose is independent of scientific values.
newsection=re.sub(r'(?<=[A-Za-z])(?=\d)', ' ',newsection);newsection=re.sub(r'(?<=\d)(?=[A-Za-z])',' ',newsection)
body=body.replace('## 7. Limitations and conclusion',newsection+'## 7. Limitations and conclusion')
for term in ['COMPLETION_ACCURACY_ONLY','forked worker','scheduler handoff','single permitted implementation repair','NaN','immediate submission']:assert term not in body,term
assert body.index('## Matched support-protocol continuation')<body.index('## 7. Limitations')<body.index('## References')
(PAPER/'DAC_REWRITE.md').write_text(body)
# Renderer is an isolated copy of the existing pure Markdown->TeX conversion, not its result-generating side effects.
renderer=(CODE/'render_paper.py').read_text();subprocess.run([sys.executable,str(CODE/'render_paper.py'),str(PAPER)],check=True)
for i in range(2):
 with (PAPER/f'compile_pass{i+1}.txt').open('w') as log:subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=PAPER,stdout=log,stderr=subprocess.STDOUT,check=True)
pdftext=subprocess.check_output(['pdftotext',str(PAPER/'main.pdf'),'-'],text=True)
for forbidden in ['COMPLETION_ACCURACY_ONLY','forked worker','scheduler handoff','NaN']:assert forbidden not in pdftext
(PAPER/'SOURCE_OF_TRUTH.md').write_text('DAC_REWRITE.md is the sole editable main text. Generate main.tex with experiments/dac_support_mismatch_resume_20261114/render_paper.py PAPER_DIR, then run pdflatex twice. Do not edit generated TeX independently. The mechanism section precedes limitations and references in both outputs. Scientific numbers are generated from the CSVs in the matching results directory. Earlier papers and their management prose remain preserved historical artifacts.\n')
(DOC/'PAPER_DELTA.md').write_text(f'''# Evidence mapping for cleaned manuscript

The paper now reports completed matched continuation, not the old preflight attempt. The original manuscripts remain unchanged. All development/repair, scheduler, submission-readiness and state-enum prose is retained in audit documents, removed from the new paper. Existing scientific negative results remain.

- Historical support counts and paired source protocol: FROZEN_PLAN, EPISODE_PROVENANCE, CHECKPOINT_LINEAGE and DATA_MANIFEST.
- All12 endpoints and256 cells completed: PIPELINE_SUCCESS, endpoint COMPLETED receipts and EVALUATION_COMPLETED.
- Added abstract mean D/I/G and full per-seed mechanism table: EFFECTS_BY_SEED.csv (new explicit table/group metric; old E1 tables retain their old aggregation).
- Conditional G interval: EFFECT_SUMMARY.csv, paired four-group bootstrap with fixed3 training seeds.
- Original-support retention: high cohort in EFFECTS_BY_SEED_BUDGET.csv.
- P99 tail comparison and source CPU: TAIL_PAIRED_DIFFERENCES.csv and ENDPOINT_COSTS.csv.
- No new transfer/PEX/STA or solver gain: scope, resource ledger and absence of new corresponding runs. Global decision remains COMPLETION_ACCURACY_ONLY outside the paper's academic prose.

Sole primary source: paper/dac_mechanism_resume_20261114/DAC_REWRITE.md; generated main.tex and compiled main.pdf share the same section order. New sentence claims cannot be broadened beyond this retrospective FEM cohort. Final mechanism state {status}; local state {local}. No new independent confirmation population was collected.
''')
atomic_json(OUT/'PAPER_SUCCESS.json',dict(status='success',attempt_id=ATTEMPT,paper=str(PAPER.relative_to(ROOT)),markdown_sha256=sha(PAPER/'DAC_REWRITE.md'),tex_sha256=sha(PAPER/'main.tex'),pdf_sha256=sha(PAPER/'main.pdf'),primary_source='DAC_REWRITE.md',management_terms_removed=True,old_papers_preserved=True))
print('FINAL_REPORT_AND_PAPER_COMPLETE',status,local,flush=True)
