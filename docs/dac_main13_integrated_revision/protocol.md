# Protocol and access boundaries

The frozen machine-readable protocol is configs/dac_main13_integrated_revision/protocol.yaml.
Fig.4: three domains, five support/protocol regimes, four ratios and five mask seeds;
no conditions removed. Reaggregation uses ensemble-prediction SSE/SST, process/family/
component normalization, then mask averaging. Strict and float32-scale tolerance
counts are separate. Stronger-baseline minimum is analysis only. Independent-unit
resampling keeps all within-group queries and masks together; FEM/Transfer have
four/two process-layer groups. No future failure-probability inference is justified.

Three deployment protocols remain separate:
1. Existing fixed-node rule-export, B4/B8, three support seeds: 83 held-out tables.
2. Existing full-characterization compute-table preparation: 68 matched tables,
   49,657 populated slots; full measured rows retained.
3. New sparse-native compute-table preparation: structurally match held-out
   finite OVER/UNDER/OVERUNDER rules (72; ASAP7 38, GF180 7, IHP 17, Sky130HS 10),
   remove hidden rows before construction, preserve S and constant resistance.
   All four arms share sparse rule bytes, native grid, width mapping, fallback,
   library/layout/SDC, units and assembly. The 12 other native holdout tables
   are explicitly excluded by short/diagonal/special rules, unchanged in every arm.
   These are not reductions of the entire rule library or resistance budget.
   Sparse geometry can change range and protected slots; eligibility is defined
   from S-only native structure before reading prediction error. Extra excluded
   contexts, if any, are recorded per input receipt, never silently dropped.

Hidden-label poison tests change all sealed capacitances in a test copy while
leaving S/coordinates/context fixed. Row deletion yields identical sparse input
bytes; predictor receives a separate S-only support.json; extraction and getters
are compared. Golden full rules are read only on the reference side and never
rewritten. Smoke tests use ASAP7 AES and IHP AES B4/s11. Matrix starts only after
both pass. Four arms x 8 layouts x 2 budgets x 3 seeds = 192 dependent arm-settings.
Endpoint/net key sets must match, nonfinite endpoints are counted. Sign convention:
positive candidate-minus-reference slack is optimistic; negative is pessimistic.

C1/C3 retain source fitting, three members, original 24k/12k updates and final-step
selection, with no new architecture or tuning grid. C1 removes NN/NN-Clip/hidden
state, learns a numerical gate; C3 removes agreement at training and inference.
C2 fixes per-member nonnegative candidate weights using source fitting only:
three 30%-holdout protocols with seed11 per source table, family/table balanced
source-scaled Huber, 300 Adam steps at .05, final step, one frozen configuration.
Source selection is evaluated separately before confirmation. Candidate outputs
and validity are frozen, then fused per member before ensemble averaging. This
is post-hoc gating control, not retraining a full fixed-fusion predictor.

Timing distinguishes reusable inventory/model/support preparation, prediction,
native construction/injection (already within PEX), SPEF, STA and output. New
single-worker release timing runs share the host with bounded training and do
not establish a stable speedup. Source label generation, exhaustive training and
target acquisition remain unmeasured when no direct receipt exists. N=10/100
reuse figures are models under identical rule/support/policy cache assumptions,
not new measurements; layout/libs and SPEF/STA scope is stated explicitly.

## Diagnostic case rule (before new candidate outputs)

Score every condition. For a compact narrative select, in each domain, the
condition with Full's smallest stronger-baseline margin, the worst regression
of each simplified variant, and each simplified variant's largest improvement
over Full. Resolve exact ties lexicographically by support/protocol/ratio.
All cases are post-hoc descriptions of the same confirmation data, not a new
independent confirmation or justification for choosing per-query methods.
Save per-member candidate output, validity, weights, weighted corrections and
support descriptors before separate scoring computes errors and direction.
MLI status/error accounting is a cross-tab of complete cell, sparse extension,
explicit clamp, inside/outside support and boundary protocol, not a disjoint
funnel. A low full-domain average does not establish per-rule dominance.

## Derived-analysis clarifications

Native paired intervals use10000 process-cluster resamples with seed20261117;
all layouts, budgets and support repeats from one process stay together. With
only four process clusters they are descriptive sensitivity ranges. Per-cell
three-seed gap ranges are also retained. This adds no experiments or selection.
The diagnostic largest simplified advantage means the largest absolute macro
NRMSE difference Full minus that simplified variant, with lexical tie order.

MLI status replay reclassifies120 singleton-support zero-valued Public requests
from archived complete-cell to explicit-clamp. Original files remain unchanged;
all60 MLI error cells reproduce. mli_status_reconciliation.json records counts
and differences. New status-specific error tables use the corrected geometry
classification and never retroactively change the coverage performance universe.

Sparse-native prep/cold totals are explicitly modeled sums of measured stages;
MLI needs no neural checkpoint loading. The shared all-model load is charged
conservatively to Binary/Full. Native-sparse requires neither injection inventory
nor prediction; its input-release cost was separately replay-timed with warm/
uncontrolled cache, not claimed as a measured standalone cold launch.
