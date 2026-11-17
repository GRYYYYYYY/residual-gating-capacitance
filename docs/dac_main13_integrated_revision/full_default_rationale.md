# Full as the empirical default

The fixed Fig.4 universe is retained: 60 dependent domain/support/holdout cells,
five mask seeds, unchanged ensemble-prediction macro NRMSE. Reaggregation matches
archived plotted values within 4.45e-16. No image-based counts or condition filtering.

| Variant | Beats OpenRCX | Beats MLI-ext. | Beats both | Worst error ratio | Minimum margin |
|---|---:|---:|---:|---:|---:|
| Ungated | 54 | 52 | 50 | 1.777980222 | -77.798022% |
| Binary | 58 | 55 | 55 | 1.348656071 | -34.865607% |
| Full | 60 | 60 | 60 | 0.947531672 | +5.246833% |

Strict and predefined float32-scale tolerance counts agree for these variants.
Worst ratios use the lower error of the two kernel controls as an analytic
reference, not a deployable oracle. Full wins 49/60 against Binary and 55/60
against Ungated; those local simplified wins remain valid.

Full's narrowest margin is Transfer In/block at 10% holdout. Its paired gap
interval crosses zero and the domain has only two independent layer groups.
Thus point-estimate coverage does not imply statistical elimination of regression,
per-query or per-table superiority, future failure probabilities, or safety under
arbitrary distribution shift. The selection rationale is retrospective.

The rationale is comparative consistency over the two specified kernel baselines,
not dominance over all numerical controls. MLP/GP and full-support Anchor advantages
remain visible. No target-label selector or runtime Full/Binary switch is introduced.

Deployment protocols remain separate. Old fixed-node rule-export favors Binary
in 10/16 net-C, 12/16 WS and 10/16 P99 comparisons against Full. New sparse-native
Full beats Binary on all16 cells for net-C/WS/P99, but beats Native-sparse only
7/16,9/16,7/16. This does not invalidate the measured offline consistency; it does
rule out transferring that consistency into a universal native-accuracy claim.
The Full default is retained with these explicit limits.

Numerical basis, adaptive gating and agreement contributions require the separate
frozen-candidate diagnostics and matched C1/C2/C3 results. They cannot be inferred
from the above three-variant comparison alone; see mechanism_attribution.md when
that evidence is finalized.
