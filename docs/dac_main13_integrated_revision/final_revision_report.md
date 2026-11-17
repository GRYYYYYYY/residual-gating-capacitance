# Final integrated revision report

Workspace: /inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114
Branch: revision/dac-cap-main13-integrated
HEAD: b97f90b7d2acd2f06dd7dd9a5f8032001faea422
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

| Method | Both strict/tolerance (of60) | Worst ratio | Mean cell error | Beats Full |
|---|---:|---:|---:|---:|
| full_replay | 60/60 | 0.947532 | 0.087864 | -- |
| fixed_fusion | 51/51 | 12.442919 | 0.428547 | 1/60 |
| numerical_gate | 29/23 | 6.240126 | 0.518712 | 8/60 |
| no_agreement | 59/59 | 1.035914 | 0.090219 | 26/60 |

C3 improves over both in 59/60 cells. The difference from Full supports a conditional agreement effect in this recipe, not calibrated uncertainty or a no-regression guarantee.

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
