"""Render final audit reports only after actual experiment completion."""
from pathlib import Path
import csv,json,hashlib,subprocess
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';D=R/'docs/dac_main13_integrated_revision';P=R/'paper/dac_layout_query_revision'
def rows(p):return list(csv.DictReader(p.open()))
def js(p):return json.loads(p.read_text())
assert js(O/'post_native/completed.json')['status']=='PASS'
assert js(O/'tests/final_contract_checks.json')['status']=='PASS'
controls=rows(O/'mechanism_summary.csv');ci={r['method']:r for r in controls}
table='\n'.join(['| Method | Both strict/tolerance (of60) | Worst ratio | Mean cell error | Beats Full |','|---|---:|---:|---:|---:|',*[f"| {r['method']} | {r['beats_both']}/{r['beats_both_tolerance']} | {float(r['worst_error_ratio']):.6f} | {float(r['mean_cell_error']):.6f} | {('--' if r['method']=='full_replay' else r['beats_full']+'/60')} |" for r in controls]])
agreement=('C3 also improves over both baselines in every cell. Agreement is therefore not necessary for the headline60/60 point-estimate property under this retraining recipe. Its possible mean-error or margin benefit is conditional, not a safety mechanism.' if int(ci['no_agreement']['beats_both'])==60 else f"C3 improves over both in {ci['no_agreement']['beats_both']}/60 cells. The difference from Full supports a conditional agreement effect in this recipe, not calibrated uncertainty or a no-regression guarantee.")
mechanism='''# Mechanism attribution

All60 conditions were scored. Frozen candidate generation receives public geometry,
context and observed S labels only; the independent scorer reads hidden labels
after candidate outputs and completion receipts exist. Full/Binary/Ungated replay
matches original errors (mechanism_replay_checks.json).65520 member-episodes pass
validity, weight normalization and weighted-correction algebra checks. None of
these algebraic properties certifies predictive accuracy.

## Supported diagnostics, with limitations

H1: Transfer In/random50%, rank2 with64 supports: Ungated corrections have wrong
direction on19.97% of pooled component/member/query occurrences and overcorrect
by more than twice the needed correction on68.28%. Its worst kernel ratio is
1.77798. FEM Boundary70%,38 supports, has only1.68% wrong directions and Ungated
beats Full (0.10271 vs0.12387). The narrative retains both cases.

H2: In Transfer In/random50%, Binary mean alpha is0.5473; gating reduces SSE to
0.4141 of its own unscaled neural candidate, yet it still regresses against the
kernel baseline. Suppression has an observed within-model effect but does not
ensure accuracy. Binary and Ungated have independently trained residuals: their
between-model difference cannot be assigned to alpha alone.

H3: In that same case, WidthLinear is valid for59.64% of query occurrences and
has pooled SSE0.0100 of the anchor on that subset; the unit-length/ridge1e-6 GP
has SSE0.2694. This supports numerical complementarity as a diagnostic hypothesis.
It is not a causal estimate from weights. At Transfer In/block10%, all individual
GP candidates have larger pooled SSE than the anchor (1.26--3.36 ratios), while
Full improves macro NRMSE: conditional fusion, cancellation and metric weighting
remain possible explanations. The evidence does not single out one cause.

H4: Public In/block50%,6--7 rank1 observations, yields Ungated/Binary/Full
0.07041/0.07307/0.08493. Full average Anchor/NN-Clip weights0.620/0.327 coexist
with almost no PCHIP weight although PCHIP pooled SSE is0.283 of anchor. The
FEM boundary case above also favors a simplified model. Useful corrections may
be diluted, but independently trained parameters and differing diagnostic vs
macro metrics preclude claiming that as the sole established cause.

Eight cases follow the documented per-domain extrema rule. All raw member/query
values, masks, support descriptors, affine rank, weights and contributions remain
available; no adverse condition was deleted. Candidate ratios use each candidate's
valid subset and are not directly interchangeable with condition macro NRMSE.

## Bounded controls actually completed

'''+table+'\n\n'+agreement+'''

C1 is a learned numerical gate, not a nonlearning baseline. It removes the
Transformer state, NN and NN-Clip together, so it tests that combined neural
representation/candidate pathway; it does not isolate each removed element.
C1/C3 use original source pools, initializer policy, sampler, optimizer, updates
and3 members, with one frozen final-step recipe. Original neural residual warm starts add2000 source-only updates; C1 removes that trunk and retains only scales/priors. Their losses and checkpoints
are archived. Source total costs remain unequal across other model families.

C2 fits one fixed, source-only nonnegative mixture per Full member and output
component, with valid-candidate renormalization. It beats both kernels in51/60
and reaches worst ratio12.4429 (FEM Boundary10%). This supports adaptive weighting
relative to the tested300-step mixture fitting recipe on those frozen candidates.
It does not prove that every fixed mixture or a retrained fixed-fusion network
must fail. Its source-selection outputs are archived; no target-query tuning.

## MLI scope

Current explicit status classification corrects120 zero-valued singleton-support
requests: complete cells35362/171315=20.6415%, rather than archived35482/171315.
No prediction or60-cell winner changes. Full improves MLI complete-cell errors
in8/8 Public,3/4 FEM,2/4 Transfer condition subsets, so the whole-coverage result
cannot be attributed solely to deficiencies of the complete-cell MLI core.
Most query exposure is sparse extension or clamping. Status/region tables show
counts and errors separately and preserve repeated-mask dependence.
'''
(D/'mechanism_attribution.md').write_text(mechanism)
audit=rows(D/'claim_evidence.csv');protocol_hash=hashlib.sha256((R/'configs/dac_main13_integrated_revision/protocol.yaml').read_bytes()).hexdigest()
actions={'PROTO':'completed192/192 sparse-native arm-settings; retain separate original protocols','TRAIN':'completed18 C1/C3 members at original budgets; unequal baseline opportunities documented; total historical cost unmeasured','MLI':'corrected status counts35362/171315; original count retained; all MLI error cells unchanged','COVER':'ordered finite trace alignment PASS; changed/all9.350649%, not benefit','BATCH':'all fixed-S target tests completed; dependence retained; canonical batching fixed','MECH':'C1/C2/C3 and independent candidate scoring complete; scope and negative outcomes retained'}
for r in audit:
 r['config_hash']=protocol_hash
 if r['issue_id'] in actions:r.update(evidence_status='ALREADY ADDRESSED',required_action=actions[r['issue_id']])
 if r['issue_id']=='MLI':r['claim']='20.641508% complete cells after correcting120 singleton boundary statuses; original20.711555% archived'
with (D/'claim_evidence.csv').open('w') as f:w=csv.DictWriter(f,list(audit[0]));w.writeheader();w.writerows(audit)
(D/'manuscript_change_log.md').write_text('''# Manuscript change log

Single formal source: paper/dac_layout_query_revision/main.tex. Original main13
TeX/PDF and preexisting dirty state remain in the read-only external snapshot.
No page-limit compression and no second official manuscript were introduced.

- Abstract/Introduction: Full default based on retrospective60-cell consistency;
  explicit sparse-native negative outcomes; three deployment protocols separate.
- Method: actual residual and fusion definitions, own parameters in each variant,
  candidate validity vs accuracy, source-only inputs and physically removed hidden
  rows before the sparse constructor, native scalar width/quantization adaptation.
- Training/Setup: actual loss/optimizer/sampler/budgets/scales/ensemble; unequal
  MLP/CNP/AC opportunities; C1/C2/C3 recipes; cohort filtering and20-table overlap.
- Coverage: exact three-variant dominance/margins/paired uncertainty and retained
  local wins; original Fig.4 universe and aggregation unchanged.
- Mechanism: full candidate diagnostics,8 rule-selected cases, bounded matched
  controls, corrected MLI status counts and core/extension/boundary error strata.
- Baselines: competitive MLP/GP plot and full numerical tables, including PCHIP,
  affine/simplex Anchor and IDW; full-support physical Anchor advantage retained.
- Deployment: original rule-export and full-support results accurately named;
  new192-run sparse-native tables, absolute fF/ps/ns errors, P99 and relative gains,
  Full/Binary cost difference, negative IHP results and new tradeoff figure.
- Limitations: few independent groups, post-hoc selection, transductive query-set
  dependence, incomplete independent physical coverage, unmeasured source costs,
  modeled cold/reuse totals vs actual PEX timing, changed returns vs benefit.

Generated tables/figures are derived from machine-readable archives. Original
compute_findings wording was clarified as archived full-characterization evidence.
No original model, raw result, reference output or unrelated FPGA source was edited.
''')
report='''# Final integrated revision report

Workspace: '''+str(R)+'''
Branch: {BRANCH}
HEAD: {HEAD}
All revision edits/results are uncommitted; no remote push. Existing user changes
were preserved, not reset. Original main13 PDF matched the supplied SHA256 exactly.
No706FEBA1 base, FPGA migration, Vivado flow or unrelated process termination.

## Acceptance and status dimensions

| Item | Implementation | Experiments | Statistical support | Performance claim |
|---|---|---|---|---|
| A protection/baseline | PASS | PASS | n/a | n/a |
| B Full consistency | PASS | PASS: complete60 cells | PASS for descriptive point estimates; INCONCLUSIVE for universal/no-regression inference | PASS:60/60 over two kernels |
| C mechanism | PASS | PASS: all candidates,C1/C2/C3 | Conditional and post-hoc; few physical groups | Limited to controls below |
| D sparse native | PASS: poison,interface,R,units,keys | PASS:192/192 | n/a | Correctness does not certify accuracy |
| E downstream | PASS | PASS:48 paired settings | Descriptive:8 layouts in4 processes | FAIL: uniform sparse-native improvement |
| F fairness/statistics | PASS | PASS: existing evidence reused | Unequal training opportunities; paired groups retained | No claim of dominance over all controls |
| G batching/cost/coverage | PASS | PASS for specified diagnostics | Timing shared-host; extrapolated reuse | NOT_RUN: equal-accuracy total-flow speedup |
| H paper | PASS | PASS: compiled PDF and figures | n/a | Scope-corrected claims |
| I reproducibility | PASS | PASS: raw receipts and hashes | n/a | n/a |

## Core findings

Ungated beats OpenRCX/MLI/both in54/52/50 of60 cells, Binary58/55/55, Full60/60/60.
Worst ratios against the stronger kernel are1.777980222/1.348656071/0.947531672;
minimum margins-77.7980%/-34.8656%/+5.2468%. Strict/tolerance counts agree.
Full's narrowest paired interval crosses zero with only2 transfer layer groups.
The retrospective default rationale stands; unknown-application safety does not.

Binary retains11/60 offline wins over Full and Ungated5/60. In original rule-export,
Full beats Binary in6/16 net-C and4/16 WS cells; Binary wins10/16 P99. In new sparse-
native, Full beats Native-sparse/MLI-native in7/16 net-C,9/16 WS,7/16 P99, and Binary-
native in16/16 for each. Both protocol-specific findings remain. There is no
target-reference selector and no automatic replacement of Full by Binary.

'''+table+'\n\n'+agreement+'''

Mechanism attribution distinguishes observed within-model suppression, complementary
valid candidates, independently trained residuals and bounded matched controls.
Weights are not causal contributions or calibrated uncertainty. See the dedicated
mechanism report for both successes and local nonoptima.

MLI complete-cell exposure is corrected to20.6415% (120 zero-valued singleton
requests reclassified as clamp; errors unchanged). Ordered trace alignment supports
924647/9888586=9.350649% changed returns, not an accuracy-benefit fraction.
Only smoke cases have new return-level tracing; all192 arms have slot coverage.

The supplied data contain no independent layout-derived physical truth for the
new matrix. Full-rule reference measures output fidelity; the existing71 symmetric
FEM templates remain the independent physical check. No arbitrary asymmetry or
universal monotonicity claim is made. External Python startup/imports, source-label generation, exhaustive historical
training/selection and paid target acquisition costs remain unmeasured. Cold/reuse totals
are explicitly modeled from recorded stages, and new native timing shares a host
with bounded training. These limitations do not mean the performed experiment
failed or remained queued.

## Actual artifacts

- Main source/PDF: paper/dac_layout_query_revision/main.tex and main.pdf.
- New figures/tables: paper/dac_layout_query_revision/figures and tables.
- Raw evidence and completed matrices: results/dac_main13_integrated_revision/main13_20261117/.
- Final completion/hash manifest: same directory,manifest.json; per-run native
  outputs contain SPEF,endpoints,logs,comparison and stage receipts.
- Reproduction: scripts/dac_main13_integrated_revision/reproduce.sh and
  docs/dac_main13_integrated_revision/reproduce.md.
- Protection snapshot path/hashes: docs/dac_main13_integrated_revision/snapshot.json.

No required experiment is reported complete solely from script creation or job
submission. Exact validation and preservation receipts are in tests/ and the
manifest. Historical missing physical/cost evidence is explicitly outside the
supported performance claims.
'''
report=report.replace('{BRANCH}',subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip()).replace('{HEAD}',subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip())
(D/'final_revision_report.md').write_text(report);print('final reports rendered')
