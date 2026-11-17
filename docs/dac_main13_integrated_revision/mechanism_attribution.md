# Mechanism attribution

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

| Method | Both strict/tolerance (of60) | Worst ratio | Mean cell error | Beats Full |
|---|---:|---:|---:|---:|
| full_replay | 60/60 | 0.947532 | 0.087864 | -- |
| fixed_fusion | 51/51 | 12.442919 | 0.428547 | 1/60 |
| numerical_gate | 29/23 | 6.240126 | 0.518712 | 8/60 |
| no_agreement | 59/59 | 1.035914 | 0.090219 | 26/60 |

C3 improves over both in 59/60 cells. The difference from Full supports a conditional agreement effect in this recipe, not calibrated uncertainty or a no-regression guarantee.

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
