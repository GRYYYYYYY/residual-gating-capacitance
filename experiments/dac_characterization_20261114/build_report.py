"""Generate evidence-linked decision, Markdown and compilable research manuscript."""
import csv,json,re,shutil,subprocess
from common import *
R=ROOT/'results/dac_characterization_20261114';S=R/'summary';D=ROOT/'docs/dac_characterization_20261114';PAPER=ROOT/'paper/dac_revision_20261114'
def read(name):return list(csv.DictReader((S/name).open()))
curves=read('budget_curves.csv');native=read('downstream_means.csv');thresholds=read('threshold_summary.csv');paired=read('paired_attainment.csv');cis=read('paired_bootstrap.csv')
assert json.loads((S/'downstream_status.json').read_text())['complete']
def value(s,m,b,key='nrmse'):
 return float(next(r[key] for r in curves if r['setting']==s and r['method']==m and int(r['budget'])==b and r['strategy']=='farthest'))
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,row))+' |\n' for row in rows)
def pair(setting,method):return next(r for r in paired if r['setting']==setting and r['comparator']==method and r['threshold_index']=='1')
cost_evidence=[]
for setting in ('reference','to_asap7'):
 a=pair(setting,'anchor');m=pair(setting,'mlp_adapt')
 cost_evidence.append(f"{setting}: at the frozen per-table threshold {next(r['threshold'] for r in thresholds if r['setting']==setting and r['threshold_index']=='1')}, all {a['both_reached']} table/seed trajectories reach the threshold for both full and anchor. Their summed replayed fine-only CPU work is {float(a['sum_full_fine_cpu_seconds_both_reached']):.2f} versus {float(a['sum_comparator_fine_cpu_seconds_both_reached']):.2f} seconds. Full and adapted MLP instead require identical measured budgets in all {m['equal']} trajectories, with identical recorded characterization work. These sums count repeated experimental trajectories; they are not a unique PDK build cost.")
cost_evidence='\n\n'.join(cost_evidence)
methods=['cmi','anchor','affine','gp','mlp_adapt','cnp','residual','binary','full']
main=[]
for s in MODELS:
 for b in ([4,8] if s=='public' else [4,8,16,32,64]):main.append([s,b]+[f'{value(s,m,b):.4f}' for m in methods])
main_table=table(['Setting','B']+methods,main)
# Compare downstream methods in each of 16 case/budget cells, seed means.
lookup={(r['case'],r['method'],int(r['budget'])):r for r in native}
cases=sorted({r['case'] for r in native});wins={}
for comparator in ('cmi','anchor','affine','binary'):
 wins[comparator]={metric:sum(float(lookup[c,'full',b][metric])<float(lookup[c,comparator,b][metric]) for c in cases for b in (4,8)) for metric in ('net_cap_nrmse','ws_abs_ns','slack_mae_ns')}
nt=[]
for c in cases:
 for b in (4,8):
  f=lookup[c,'full',b];a=lookup[c,'cmi',b];nt.append([c,b,f"{float(a['net_cap_nrmse']):.5f}",f"{float(f['net_cap_nrmse']):.5f}",f"{float(a['ws_abs_ns']):.6g}",f"{float(f['ws_abs_ns']):.6g}",f"{float(f['slack_p99_ns']):.6g}",f"{float(f['tns_abs_ns']):.6g}"])
native_table=table(['Layout','B','CMI net NRMSE','Full net NRMSE','CMI WS abs ns','Full WS abs ns','Full slack P99 ns','Full TNS abs ns'],nt)
tt=[]
for s in MODELS:
 for m in ('anchor','affine','gp','mlp_adapt','binary','full'):
  r=next(r for r in thresholds if r['setting']==s and r['method']==m and r['threshold_index']=='1');tt.append([s,m,f"{float(r['threshold']):.4f}",f"{r['reached']}/{r['trajectories']}",r['not_reached'],r['median_budget_conditional_on_attainment']])
threshold_table=table(['Setting','Method','Error threshold','Reached trajectories','Not reached','Median B among reached'],tt)
costs=read('target_cost_curve.csv');ct=[]
for setting in MODELS:
 for budget in ([4,8] if setting=='public' else [4,8,16,32,64]):
  f=next(r for r in costs if r['setting']==setting and r['method']=='full' and int(r['budget'])==budget);m=next(r for r in costs if r['setting']==setting and r['method']=='mlp_adapt' and int(r['budget'])==budget)
  ct.append([setting,budget,f"{float(f['mean_recorded_fine_cpu_seconds']):.2f}" if f['mean_recorded_fine_cpu_seconds'] else 'unknown',f"{float(f['mean_recorded_validated_cpu_seconds']):.2f}" if f['mean_recorded_validated_cpu_seconds'] else 'unknown',f"{float(f['mean_completion_adaptation_wall_seconds']):.4f}",f"{float(m['mean_completion_adaptation_wall_seconds']):.4f}"])
cost_table=table(['Setting','B','Recorded fine CPU s','Recorded validated CPU s','Full completion s','MLP adaptation+completion s'],ct)
att=[]
for s in ('reference','to_asap7'):
 for b in (4,8,16,32,64):att.append([s,b,f'{value(s,"attentioncap_adapted",b):.4f}',f'{value(s,"mlp_adapt",b):.4f}',f'{value(s,"full",b):.4f}'])
attention_table=table(['Setting','B','Adapted AttentionCap','Adapted MLP','Full'],att)
reverse=json.loads((R/'reverse_transfer/COMPLETED.json').read_text())
# Decision is deliberately limited; direct adaptation is a strong counterexample.
status='COMPLETION_ACCURACY_ONLY'
assert value('reference','mlp_adapt',4)<value('reference','full',4) and value('to_asap7','mlp_adapt',4)<value('to_asap7','full',4)
decision=f'''# Final decision

**{status}**

The new experiment supports conditional rule-completion and a measured cost/accuracy tradeoff. It does not establish a general characterization-efficiency advantage over strong equal-observation baselines, or universal necessity of full gating. Do not submit the planned broad efficiency/routing claim on this evidence alone. This is a completed bounded research revision, not an acceptance or submission-readiness claim.

## Gate 1: characterization efficiency

FEM B4 full NRMSE {value('reference','full',4):.4f} versus same-S adapted MLP {value('reference','mlp_adapt',4):.4f}; at B8 {value('reference','full',8):.4f} versus {value('reference','mlp_adapt',8):.4f}. Transfer B4 is {value('to_asap7','full',4):.4f} versus {value('to_asap7','mlp_adapt',4):.4f}; at B64 {value('to_asap7','full',64):.4f} versus {value('to_asap7','mlp_adapt',64):.4f}. Thus large advantages over the own anchor alone do not prove a characterization advantage over the strong learning control.

{threshold_table}

Thresholds are source-validation anchor-error quantiles, not application-certified tolerance requirements. Three data seeds per table are repeated observations, not independent technologies. The median is conditional on attainment and must be read with censored counts. Paired per-table comparisons, including one-sided/neither attainment, are in paired_attainment.csv. No extrapolation between budgets. Public accesses are simulated entries, so no measured field-solver saving follows. FEM costs are replayed original fine-only and coarse+fine+wide CPU records; no new solver wall speedup was measured. New training/target fitting costs are separate and historical source-pretraining CPU/GPU totals remain incomplete. No amortized total-cost superiority claim is licensed.

{cost_evidence}

{cost_table}

The CPU columns are mean recorded characterization work per table for the same support; completion columns are new wall measurements. They are not added into an end-to-end speedup.

## Gate 2: mechanisms and deployment

Observation conditioning and learned correction have useful scope relative to numeric anchors. The adapted-MLP result shows that target parameter fitting can explain much of the rank2 benefit. Full-versus-binary/residual differences vary with budget and setting; training-seed sensitivity and pointwise group bootstrap are separately available. All three source-validation comparisons rejected linear-only pruning under the registered strict error rule; its confirmation rows are labeled ablation, not selected deployment. No additional router search was performed. GP/anchor choices, routing, target adaptation and acquisition are separate factors.

Native full wins over CMI on net-C error in {wins['cmi']['net_cap_nrmse']}/16 and absolute WS deviation in {wins['cmi']['ws_abs_ns']}/16 case/budget seed-mean cells. Against binary those counts are {wins['binary']['net_cap_nrmse']}/16 and {wins['binary']['ws_abs_ns']}/16. All 240 budget native runs plus eight golden replays completed. Original 84 holdout tables include one ineligible short table, left golden; 83 eligible tables are changed identically across methods. Full-rule reference, R, layouts, SDC, libraries and executable hashes are fixed. Unmodified rule tables remain fully characterized for every method, so the budget is not a whole-PDK characterization budget. These are extraction/STA fidelity measurements, not chip performance, timing closure or signoff accuracy. Native failure coverage, P99 slack, TNS and endpoint/path/FN/FP results are retained.

## Gate 3 and stop

End state is {status}. E1--E4, finite related-work adaptation, reverse direct-MLP transfer, correctness checks, plots and editable research paper are delivered. No further models, solver geometries or router searches are queued. Historical negative fixed-mask outcomes remain unchanged. The 770.07 CPU-second public execution failure and the administrative native scheduler handoff are explicitly archived. All original processes/data and publication artifacts were preserved; no remote push/publication/submission occurred.

AttentionCap is an official-backbone/head **adaptation**, not its original benchmark; component-only supervision and explicit boundary/material features are disclosed. Tsai comparison is a paper-inspired direct MLP, not the authors' original pipeline; their unseen-thickness capability is acknowledged. Flash-CNNCap remains a task-scope comparison, not a mismatched LUT-image experiment. General claims beyond these comparisons remain unsupported.
'''
(D/'FINAL_DECISION.md').write_text(decision)
claims=[
('Fixed-budget public completion improves over numeric interpolation','supported','summary/budget_curves.csv; confirmation_public/records.jsonl.gz','338 eligible rank1 tables; B4/B8; three data seeds','simulated source-rule access, not measured solver saving','Support-conditioned completion improves sparse public-rule prediction in the evaluated cohort.'),
('Full gating generally reduces characterization work relative to strong baselines','not supported','summary/paired_attainment.csv; summary/budget_curves.csv','all registered settings and feasible budgets','same-S adapted MLP dominates important rank2 conditions; binary competitive','No general characterization-work superiority is established.'),
('Actual solver or end-to-end wall-clock speedup','not measured','geometry_cost_index.csv; summary/cost_ledger.csv','recorded numerical CPU cost and measured completion/native times','no same-condition fresh sparse/full solver timing; incomplete source costs','Recorded target characterization work and measured completion cost are reported separately.'),
('Full gate is universally necessary','not supported','summary/paired_bootstrap.csv; member_sensitivity/summary.json','three historical training seeds; fixed budget Q','effects vary; pointwise intervals; few FEM dependency groups','Complex fusion has conditional benefits and is not required universally.'),
('Native rule completion preserves fixed-layout extraction/STA fidelity','supported with limits','summary/downstream_raw.csv; summary/downstream_provenance.json; export_batch_alignment.json','8 layouts, 2 budgets, 3 data seeds, 5 methods; 83 eligible holdouts','full-rule reference; failures relative to simpler methods retained','Native fidelity is measured, not signoff or timing closure.'),
('Official AttentionCap outperformed on its original benchmark','not claimed','attention/reference_confirmation; attention/to_asap7_confirmation','common FEM subset with adapted features/three-component supervision','limited 3000-step training and finite LR/adaptation candidates','An adapted official AttentionCap baseline is evaluated on the common task.'),
('Tsai requires retraining at every thickness','false','../docs/dac_characterization_20261114/RELATED_WORK_AUDIT.md','local ICCAD25 paper and author page','their thickness generalization differs from target-stack conditioning','Prior work already predicts unseen thickness without per-thickness retraining.'),
('Flash-CNNCap numerically compared','not performed by scope','../docs/dac_characterization_20261114/RELATED_WORK_AUDIT.md','3D window contribution/matrix task','no common 3D window supervision here','No full-3D-extractor superiority is claimed.'),
('Label budget is respected','supported','boundary_checks.json; learned_boundary_checks.json; export_batch_alignment.json','explicit geometry-only input allowlist, same S/Q, oracle','full-grid transductive setting; no arbitrary-query invariance','Only purchased target observations enter prediction or adaptation.'),
('Frozen source parameters imply zero target observations','false','summary/cost_ledger.csv; docs/dac_characterization_20261114/BASELINE_PROTOCOL.md','full/CNP/control methods need S','zero-observation MLP/Attention rows are information-limited controls','No target parameter updates does not mean no target observations.'),
('Broad cross-process generalization','not supported','confirmation_to_asap7; reverse_transfer/COMPLETED.json','two material stacks, reverse direct MLP only','reverse experiment is not full-gate transfer validation','Transfer evidence is limited to the declared material stacks.'),
('New confidence guarantees from soft gates','not supported','../docs/dac_characterization_20261114/BASELINE_PROTOCOL.md','no calibration experiment','branch disagreement is not confidence','No calibrated uncertainty or guaranteed safe fallback is claimed.')]
with (D/'CLAIM_EVIDENCE.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['claim','status','raw_data','statistical_scope','limitations','allowed_manuscript_statement','scripts','model_data_version'])
 scripts=['evaluate.py;summarize.py','charge_ledger.py;summarize.py','cost_index.py;profile_components.py;summarize.py','member_check.py;summarize.py','downstream.py;native.tcl;summarize_downstream.py;check_export_alignment.py','attention.py','learning.py','docs/dac_characterization_20261114/RELATED_WORK_AUDIT.md','check_boundary.py;check_learned.py;check_export_alignment.py','learning.py;summarize.py','reverse_transfer.py','docs/dac_characterization_20261114/BASELINE_PROTOCOL.md']
 for row,script in zip(claims,scripts):
  row=list(row);row[2]=row[2].replace('../docs/','docs/')
  row[2]='; '.join(x if x.startswith(('docs/','experiments')) else 'results/dac_characterization_20261114/'+x for x in row[2].split('; '))
  if not script.startswith('docs/'):script='; '.join('experiments/dac_characterization_20261114/'+x for x in script.split(';'))
  w.writerow([*row,script,'05d0717 inputs; dac-budget-v1-20261114; MANIFEST.json and per-run hashes'])
(PAPER/'results_tables.md').write_text(main_table+'\n'+threshold_table+'\n'+cost_table+'\n'+native_table+'\n'+attention_table)
body=f'''# Support-Conditioned Completion of Capacitance Rules for Parasitic Extraction

Research revision for a DAC-oriented evaluation. End state: **{status}**. This manuscript does not claim submission readiness.

## Abstract

We study offline completion of capacitance rules from a limited number of target-process geometry observations. The output is a native rule file consumed by an unchanged parasitic-extraction and static-timing flow. We evaluate a support-derived numerical anchor, conditional residual models, full numerical/neural fusion, and equal-observation numerical and learning controls on a fixed sealed query population. The protocol distinguishes simulated rule accesses, replayed finite-element characterization CPU cost, and newly measured prediction and adaptation time. The public cohort admits only budgets 4 and 8 for 338 eligible tables. On finite-element and FreePDK15-to-ASAP7 cohorts, target-adapted direct regression is a strong counterexample to universal full-gate efficiency: at four observations, its NRMSE is {value('reference','mlp_adapt',4):.4f} and {value('to_asap7','mlp_adapt',4):.4f}, compared with {value('reference','full',4):.4f} and {value('to_asap7','full',4):.4f} for full fusion. We additionally evaluate a component-supervised adaptation of official AttentionCap and native extraction/STA on eight fixed layouts. The evidence supports a bounded rule-completion study and an adaptation-versus-inference tradeoff, but not a general characterization-cost advantage or universal necessity of complex gating.

## 1. Introduction

Parasitic extraction commonly reuses a characterized geometry-to-capacitance rule library. Building this library and filling gaps in its geometric coverage are separate from applying it to a routed layout. Existing observations within a target table carry process-specific information that can be provided at inference or used for parameter adaptation. The practical question is whether that information improves a completed rule library at the same reference-query budget, or reduces the number and cost of queries needed for a declared error level.

Our deployment is offline: select and purchase target geometries, complete a fixed candidate grid, export native rules, then run existing OpenRCX and STA. This scope makes input ownership and costs explicit. We do not replace the entire extractor, learn resistance, reconstruct arbitrary three-dimensional Maxwell matrices, or claim silicon/signoff accuracy. Query extrapolation refers to current observed support; it need not exceed source-training geometry coverage.

The contribution is a reproducible, budget-accounted evaluation of support-conditioned rule completion and its native interface. A residual around a numerical anchor is a useful design, but the scientific question includes simpler residual/binary models and target-adapted direct learners. We report their failures and strengths rather than attributing every improvement over interpolation to complex fusion. Three-seed model ensembles, immutable query sets, original solver receipts and native fixed-layout runs allow the claims to be checked independently.

## 2. Related work and comparison scope

AttentionCap learns capacitance matrices from conductor geometry using a Transformer and a Laplacian head [1]. We reuse the official implementation on the common reconstructible FEM geometry, adapting its input representation for material layers and the external ground boundary. Supervision is restricted to the same three components available to all methods. This is an adapted baseline, not a reproduction of the authors' original dataset or reported error. Flash-CNNCap maps three-dimensional windows to contribution images and reconstructs capacitance matrices/netlists [2]. Its window and DEF-to-SPEF task differs from fixed-grid rule completion; we neither convert LUT sequences to artificial images nor claim numerical superiority over its complete extractor.

Tsai et al. encode geometry and layer thickness for interconnect exploration and demonstrate unseen-thickness prediction without repeated per-thickness retraining [3]. Our direct MLP is a paper-inspired implementation using the available coordinates and structural/material summaries, with finite learning-rate selection and equal-support target adaptation. It does not reproduce their full pattern extraction or layout assembly. Within-stack thickness generalization is distinct from cross-stack adaptation.

ResCap already combines a physical estimate and a learned residual [4]. Accuracy-Based Hybrid PEX selects among rule, neural and field-solver methods according to accuracy needs [5]. CNP/ANP establish conditioning on observed context sets [6,7], and AIL-DNN addresses adaptive incremental learning [8]. We do not claim first use of residual learning, hybridization, observation conditioning or adaptive sampling. Our empirical distinction is the frozen information budget and native rule-library fidelity evaluation. All reported comparisons use our matched physical definitions and NRMSE; numbers from unrelated papers are not assembled into a cross-paper ranking.

## 3. Problem and extraction interface

For a table with candidate geometries X and permitted context c, let S be purchased indices and y(S) their capacitance vectors. A predictor computes F(X,c,S,y(S)) on the entire fixed grid. The evaluator seals Q, disjoint from the candidate pool from which S can be selected. Q is unchanged across budgets, methods and sampling trajectories for a table/data seed. Unqueried candidate labels are also hidden. Source-trained normalization is fixed. Candidate and query geometry are permitted transductive inputs; invariance to a changed query set or online single-query deployment is not assumed.

A budget unit is one unique geometric reference query, including initialization. One geometry may return several components and require multiple conductor excitations; those components do not multiply the query charge. We report the excitation work separately. Repeated queries use a declared cache and cannot reveal a label before being charged. Public-rule accesses simulate observations of existing source-rule values. FEM labels derive from a two-dimensional material-stack cross section with infinite extrusion, not a general three-dimensional window.

Public outputs are coupling and ground capacitance in source-rule-native per-length units. Their 1,713 tables all have rank-one geometry variation. FEM outputs, in F/m, are summed two-sided lateral coupling, ground including both the external boundary and explicit grounded context, and diagonal coupling. Independent width and spacing parameters make the FEM grid rank two; parameter dimension and field dimension are different concepts.

The exporter substitutes only unobserved capacitance tokens on eligible held-out rows and preserves observed rows, comments, other rule rows and resistance. Of the original 84 downstream holdouts, one has insufficient points for the shared sealed-Q protocol and remains golden; 83 are eligible. All methods use this identical subset. The resulting rule file is consumed by native OpenRCX on the same routed/connected database, SDC, cell libraries and executable. Reference timing comes from the full original rule file. Other rule tables retain their already available golden values for every method. Thus the native budget applies to these selected held-out tables, not to rebuilding an entire PDK from scratch; public fitting also contains other tables from the same processes.

## 4. Method and alternatives

The support anchor is computed from S and y(S). A shared Transformer encodes geometry, structural/material context, observed values, an observation indicator and the anchor. Its residual head predicts a correction. The full model combines numerical corrections and neural raw/clamped corrections with component-wise weights, then applies nonnegativity and restores observations exactly. Classical options include PCHIP, aligned-width interpolation and six RBF-GP configurations: length multipliers 0.5/1/2 with ridge 1e-6/1e-4. The anchor is a separate control because it differs from rank-matched multilinear interpolation on sparse rank-two grids.

Full inference evaluates applicable branches before fusing them. Low gate weight does not automatically avoid branch computation. Ungated residual and binary anchor/neural controls reuse the original fitting data, warm start, architecture core, optimizer budget and three training seeds. Their actual local weights were verified and reloaded; historical fixed-mask scores were not reused as budget predictions. A linear-only dictionary mask is evaluated as a separately labeled pruning ablation. All three registered source-validation comparisons favored retaining the full dictionary under the strict error selection rule.

Other controls are explicitly implemented rank-matched multilinear interpolation, validation-selected local affine, an independently selected GP, PCHIP where applicable (anchor fallback on rank-two tables), a direct MLP, and a deterministic mean-aggregation CNP. Direct MLP target adaptation uses only the same purchased S; no early stopping or free calibration label uses Q. Zero-target MLP and AttentionCap predictions are clearly information-limited controls. The anchor-conditioned method has no defined empty-support interface and is not assigned a fabricated zero-observation result.

## 5. Experimental protocol and cost accounting

Effective public fitting/selection/confirmation counts are 1,051/246/340; FEM counts are 16/24/16; FreePDK15-to-ASAP7 counts are 8/12/8. All 84 downstream tables and duplicate content are absent from public fitting and selection. Confirmation cohorts have been used previously, so this is a new protocol on existing confirmation data, not a new blind test. Three published full members per setting and 18 matched-control members pass checkpoint hash and configuration checks.

The inherited numerical evidence retains 14,688 initial, 11,016 expanded-coverage and 10,368 boundary receipts. Mesh/boundary convergence, flux-energy consistency, reciprocity and matrix checks pass their recorded criteria. The analytic coaxial pilot has relative error 0.00026334. These checks support the declared numerical reference; mutual consistency alone is not an external three-dimensional or silicon signoff validation. No new field-solver experiment is claimed in this study.

Budgets are 4/8/16/32/64, filtered by candidate-pool size. Three data seeds 11/29/47 define fixed Q (20% with at least two points for ordinary tables). Four geometry-coverage points initialize each trajectory and count toward B. A common two-point rule applies to tables with four to seven nodes; tables with fewer than four are ineligible for every method. Public confirmation has 338 eligible tables at B4/B8 and none at B16 or larger. Primary comparisons share geometry-coverage S; random and curvature comparisons share Q and initialization but may select different later S.

Primary macro NRMSE pools squared error and squared truth within process/family/component, then averages the defined component ratios. Native MAE and table P95/P99 absolute errors accompany it. No weak-capacitance observations are removed. All-zero truth components remain in absolute metrics and are excluded only from undefined relative normalization. Failures and unavailable budgets remain explicit. Group bootstrap uses 2,000 paired resamples of dependency groups within process; repeated data seeds and all families of one FEM layer stay together. These are pointwise intervals, not uncertainty over a broad population of process technologies. Training-seed variation is reported separately at fixed data seed 11.

Two learning rates and a fixed 3,000-update endpoint are offered to new MLP/CNP and adapted AttentionCap controls; source validation selects the candidate, followed by training seeds 1/2. Target adaptation candidates are 0/50/200 updates, selected on source validation only. Local affine reuses the earlier validation choices 4/8/8. Independent GP selection uses the six registered configurations. The new MLP/CNP source sampler balances families and samples tables uniformly within family; it does not match the archived process-balanced sampler or its longer training schedule. Therefore only the archived full/residual/binary controls are matched in training budget. New models match source data and target observations with a finite selection opportunity, not globally optimized performance. No confirmation-driven router search or unbounded correction round is performed.

Error thresholds are the first, second and third quartiles of source-validation anchor table errors at B8 (or the largest feasible smaller budget). They are descriptive thresholds, not application-certified tolerances. We report the smallest measured budget attaining each threshold, preserving non-attainment rather than extrapolating an unmeasured budget. Costs distinguish unique geometry queries, original fine-only CPU work, original coarse+fine+wide validated CPU work, and measured completion/target-fitting/selection/export/native time. The 12,024 geometry-index entries link to original solver records and exact fine-matrix projections. Cached charged wall time is not substituted for characterization work. Historical source CPU/GPU cost is incomplete; no total-cost or real solver wall-speedup claim follows.

## 6. Results

### 6.1 Fixed-budget completion

{main_table}

At four FEM observations, full fusion improves over the anchor but loses to the same-support adapted MLP. The difference persists through the low and middle budgets. For transfer at B64, full is {value('to_asap7','full',64):.4f}, GP is {value('to_asap7','gp',64):.4f}, and adapted MLP is {value('to_asap7','mlp_adapt',64):.4f}. These controls prevent interpreting an interpolation comparison as evidence that complex fusion is uniquely data efficient. Full inference avoids target optimizer updates, while the MLP pays a measured fitting cost; completion_cost.pdf presents this separate tradeoff.

Public results are restricted to the feasible rank-one cohort. At B4, full/binary/anchor NRMSE is {value('public','full',4):.4f}/{value('public','binary',4):.4f}/{value('public','anchor',4):.4f}; at B8 it is {value('public','full',8):.4f}/{value('public','binary',8):.4f}/{value('public','anchor',8):.4f}. Higher FEM budgets cannot be presented as public-corpus evidence. The curves retain simple controls and do not assume that full fusion must be selected for deployment.

### 6.2 Threshold attainment and characterization work

{threshold_table}

The table retains non-attainment, and its conditional median is not a common-population saving estimate. Paired minimum-budget/cost comparisons preserve both-reached, one-sided and neither-reached outcomes. A favorable comparison to an anchor does not establish a benefit over adapted MLP or binary residual completion. Public savings refer only to simulated observations. FEM CPU numbers are recorded-cost replay; source pretraining and adaptation prevent converting them into a single measured end-to-end acceleration factor.

{cost_table}

Original fine/validated CPU seconds and new completion wall seconds are different measurements. They describe the target-phase tradeoff without asserting an amortized or measured end-to-end acceleration.

### 6.3 Same-budget adaptation and related-work control

{cost_evidence}

{attention_table}

The component-supervised official AttentionCap adaptation does not remove the stronger direct-MLP counterexample. Its finite training and modified heterogeneous-material/boundary representation limit conclusions about the original paper's method; no cross-paper benchmark ranking is made. The additional ASAP7-to-FreePDK15 direct-MLP experiment uses 8 fitting, 12 source-selection and 8 target-confirmation tables. Its pooled zero-target and adapted errors are {reverse['nrmse']['mlp_zero']:.4f} and {reverse['nrmse']['mlp_adapt']:.4f}, respectively. This is reverse-direction evidence for the direct baseline, not evidence that the full gate transfers bidirectionally. Two stacks still do not establish broad process generalization.

### 6.4 Native extraction and STA

{native_table}

All eight full-rule golden replays match archived net C and R exactly. All 240 planned budget/method/data-seed native evaluations complete with the same net and endpoint sets and unchanged R. The table reports seed means and absolute native deviations. Full improves net-C fidelity over CMI in {wins['cmi']['net_cap_nrmse']}/16 and absolute WS deviation in {wins['cmi']['ws_abs_ns']}/16 case/budget cells; versus binary, the corresponding counts are {wins['binary']['net_cap_nrmse']}/16 and {wins['binary']['ws_abs_ns']}/16. These descriptive cells share rule libraries and layouts and are not independent process samples. P99 slack, TNS, endpoint/path overlap, ranking and violation FN/FP are in the raw tables; no constraints were changed to create a favorable result. Full-rule reference agreement does not measure real-chip improvement.

### 6.5 Mechanism, failures and prior evidence

Full-versus-residual/binary comparisons and paired group intervals vary with setting and budget. Soft gate visualizations do not prove necessity or calibrated confidence. The registered pruning mask is an ablation and was not selected by source validation. No new acquisition network was built; random/coverage/curvature raw curves are retained. They change only the purchased support under a shared query and cost protocol.

For example, the public full-minus-binary NRMSE difference at B4 is -0.00851 with a pointwise 95% paired group interval [-0.01610, -0.0000880]. At B8 it is -0.00389 with interval [-0.01105, 0.000891], which includes zero. These comparisons quantify a conditional effect; they do not establish universal gate necessity, especially when most native cells favor binary. All 94 registered paired intervals are retained, along with three-training-seed ranges at fixed data seed 11; no favorable seed is selected.

Previously reported 30%-random-missing out-of-support cases remain counterexamples: FEM anchor/local-affine/full NRMSE is 0.0606/0.0621/0.0895; transfer is 0.0595/0.0594/0.0877. These are historical fixed-mask results, not new B-budget measurements. The previous public pruning speedup is also not generalized to rank-two or current low-budget inference. One new public execution attempt stalled in a forked worker, used 770.07 CPU seconds and emitted no records; its diagnostics and exact executed source are retained. Direct execution repaired orchestration without changing models or the frozen protocol. A native scheduler handoff preserved the running OpenROAD child and all outputs. Neither administrative event is hidden as successful scientific evidence.

## 7. Limitations and conclusion

The public geometry is rank one, FEM physics is idealized two-dimensional electrostatics, transfer covers only two stacks, and the available confirmation cohorts are not freshly blinded. The strongest new direct baseline uses finite source-validation tuning rather than exhaustive architecture optimization. The adapted AttentionCap feature and supervision interface differ from its original benchmark. No numerical Flash-CNNCap comparison is appropriate without a common three-dimensional window task. Historical source-generation/training CPU/GPU totals and true sparse-versus-full solver wall measurements are incomplete. Thresholds were validation-derived and are not certified downstream application requirements.

Support-conditioned completion is a useful offline rule-library interface and can improve fidelity at fixed target observation budgets. However, same-budget target adaptation and simple gates explain important benefits, and full fusion is not uniformly the efficient choice. We therefore retain the conservative rule-completion title and stop with COMPLETION_ACCURACY_ONLY. The evidence does not support the broader characterization-efficiency repositioning or justify an immediate submission on that claim. Further work would require a separately registered application threshold, stronger independent physical/deployment evidence and a clearly isolated contribution; it is not automatically launched in this study.

## References

[1] Huang et al. AttentionCap: Transformer Based Capacitance Matrix Learning Toward Full-Chip Extraction. DAC 2026 / arXiv:2606.08161. https://github.com/THU-numbda/AttentionCap

[2] Flash-CNNCap: Capacitance Extraction via Image Mapping. Official implementation, 2026. https://github.com/THU-numbda/flash-cnncap

[3] C.-Y. Tsai, S. Kim and S.-K. Lim. Capacitance Extraction via Machine Learning with Application to Interconnect Geometry Exploration. ICCAD 2025. doi:10.1109/ICCAD66269.2025.11240935.

[4] J.-C. Tsai et al. ResCap: Fast-yet-Accurate Capacitance Extraction for Standard Cell Design by Physics-Guided Machine Learning. ASP-DAC 2025. doi:10.1145/3658617.3697737.

[5] M. S. Abouelyazid, S. Hammouda and Y. Ismail. Accuracy-Based Hybrid Parasitic Capacitance Extraction Using Rule-Based, Neural-Networks, and Field-Solver Methods. IEEE TCAD 41(12), 5681–5694, 2022. doi:10.1109/TCAD.2022.3161199. Author institutional abstract: https://fount.aucegypt.edu/faculty_journal_articles/4632/

[6] M. Garnelo et al. Conditional Neural Processes. ICML 2018. https://proceedings.mlr.press/v80/garnelo18a.html

[7] H. Kim et al. Attentive Neural Processes. ICLR 2019 / arXiv:1901.05761. https://arxiv.org/abs/1901.05761

[8] AIL-DNN: Modeling of IC Interconnect Parasitic Capacitances Based on Adaptive Incremental Learning. IEEE TCAD, 2025. doi:10.1109/TCAD.2025.3562947. Detailed full-text methodological claims were not independently reverified in this run.
'''
(PAPER/'DAC_REWRITE.md').write_text(body)
# Simple, auditable Markdown-to-LaTeX rendering (no external conversion service).
def esc(s):
 urls=[]
 def protect(m):
  urls.append(m.group(0));return 'URLTOKEN'+str(len(urls)-1)+'END'
 s=re.sub(r'https?://[^\s]+',protect,s)
 s=s.replace('→',r'$\rightarrow$').replace('–','--').replace('—','---')
 for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:s=s.replace(a,b)
 s=re.sub(r'\*\*(.+?)\*\*',r'\\textbf{\1}',s)
 for j,url in enumerate(urls):s=s.replace('URLTOKEN'+str(j)+'END',r'\url{'+url+'}')
 return s
lines=body.splitlines();tex=[];i=1;table_number=0
captions=['Fixed-budget macro NRMSE; smaller is better. All methods share the same S and Q.', 'Attainment at the frozen middle threshold. Conditional medians must be read with censored counts.', 'Recorded characterization CPU work and measured completion wall time, reported separately.', 'Component-supervised adaptation of official AttentionCap, not its original benchmark.', 'Native extraction and STA fidelity against full-rule extraction; seed means.']
while i<len(lines):
 line=lines[i]
 if line.startswith('| '):
  block=[]
  while i<len(lines) and lines[i].startswith('| '):block.append([x.strip() for x in lines[i].strip('|').split('|')]);i+=1
  block=[b for b in block if not all(x=='---' for x in b)]
  cols=len(block[0]);tex.append(r'\begin{table*}[t]\centering\scriptsize\resizebox{\textwidth}{!}{\begin{tabular}{'+'l'*cols+'}'+r'\toprule')
  for j,b in enumerate(block):tex.append(' & '.join(esc(x) for x in b)+r'\\'+(r'\midrule' if j==0 else ''))
  tex.append(r'\bottomrule\end{tabular}}\caption{'+esc(captions[table_number])+r'}\end{table*}');table_number+=1;continue
 if line.startswith('### '):tex.append(r'\subsection{'+esc(re.sub(r'^\d+\.\d+\s*','',line[4:]))+'}')
 elif line.startswith('## '):
  title=re.sub(r'^\d+\.\s*','',line[3:]);tex.append(r'\section*{'+esc(title)+'}')
  if title=='Introduction':tex.append(r'\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{figures/workflow.pdf}\caption{Budgeted offline rule completion and fixed-layout extraction/STA fidelity.}\end{figure*}')
  if title=='Method and alternatives':tex.append(r'\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{figures/architecture.pdf}\caption{Support-derived anchor and jointly trained residual fusion. GP ridge values match executed code.}\end{figure*}')
  if title=='Results':
   for file,caption in [('budget_accuracy','Fixed-Q budget curves; public has no eligible table at B16 or above.'),('fixed_error_cost','Minimum measured work at the frozen middle threshold. Conditional medians and IQRs; labels retain attainment coverage.'),('completion_cost','Completion and target-adaptation wall cost versus error; characterization and historical source costs are separate.'),('gating_training_seeds','Full, residual and binary sensitivity across three source-training seeds at fixed data seed; bands are seed ranges, not confidence intervals.'),('native_fidelity_B4','Native net capacitance and worst-slack fidelity at B4. Lower deviation is better; constraints remain fixed.')]:
    tex.append(r'\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{figures/'+file+r'.pdf}\caption{'+esc(caption)+r'}\end{figure*}')
 else:tex.append(esc(line))
 i+=1
header=r'''\documentclass[10pt,twocolumn]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.7in]{geometry}
\usepackage{graphicx,booktabs,amsmath,url}
\usepackage[hidelinks]{hyperref}
\setlength{\emergencystretch}{3em}
\title{Support-Conditioned Completion of Capacitance Rules for Parasitic Extraction}
\author{Research revision}
\date{14 November 2026}
\begin{document}\maketitle
'''
(PAPER/'main.tex').write_text(header+'\n'.join(tex)+'\n\\end{document}\n')
(PAPER/'figures').mkdir(exist_ok=True)
for p in S.glob('*.pdf'):shutil.copyfile(p,PAPER/'figures'/p.name)
(D/'decision_summary.json').write_text(json.dumps(dict(status=status,native_wins=wins,all_native_complete=True),indent=2))
print(status)
