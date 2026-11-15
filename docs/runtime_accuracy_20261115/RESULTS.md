# Measured runtime–accuracy results

These are completed measurements, with the exact populations and boundaries in [REPRODUCE.md](REPRODUCE.md). The main paper is six content pages plus one reference page; the expanded treatment retains the complete timing discussion and native-agreement plot.

## Same 71 physical templates

One CPU thread; three learned members; all 153 support samples per context. The canonical Q limit is 32, with six actual batches (mean 11.83 queries/batch). Fit costs span all six contexts and are charged once. The first optimizer initialization is included.

| Method | NRMSE | Warm ms/Q | Q=1 mean ms | Q=1 P95 ms | Fit s | P95/P99 absolute (pF/m) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Anchor | 0.00451 | 0.788 | 8.643 | 8.971 | 0.00 | 0.241 / 0.357 |
| CMI | 0.00452 | 0.923 | 10.008 | 10.672 | 0.00 | 0.241 / 0.357 |
| Affine | 0.05254 | 0.232 | 2.558 | 2.650 | 0.00 | 3.400 / 4.506 |
| GP | 0.05371 | 0.316 | 3.516 | 3.604 | 0.00 | 3.509 / 3.838 |
| Residual | 0.02688 | 2.051 | 22.511 | 23.969 | 0.00 | 1.699 / 2.782 |
| Binary | 0.02218 | 2.110 | 22.971 | 24.383 | 0.00 | 1.339 / 1.481 |
| Full | 0.01675 | 3.706 | 40.973 | 44.127 | 0.00 | 1.025 / 1.569 |
| Adapted MLP | 0.01889 | 0.025 | 0.222 | 0.259 | 14.03 | 1.975 / 2.365 |
| CNP | 0.16575 | 0.155 | 1.561 | 1.767 | 0.00 | 13.050 / 14.921 |
| Adapted AttentionCap | 0.70695 | 0.230 | 1.454 | 1.532 | 11.27 | 48.096 / 51.419 |

P95/P99 pool the two nonzero physical components; component-specific values and every batch protocol are in the CSVs. No native absolute error is pooled across process-specific rule units. Anchor/CMI are more accurate than Full on this full-support cohort. Cached MLP is faster after fitting, with higher error than Anchor. The adapted AttentionCap speed is accompanied by its poor accuracy; this is not a reproduction or ranking of its original matrix-supervised task.

## Matched reference and native computation

Resident one-RHS fine solving averages 3.719 s/geometry over three complete passes. The maximum scaled target-column versus certified-row difference is 1.49e-15. Recorded cold fine-only and certification worker-wall sums are 316.11 and 799.13 s, respectively. These are different timing boundaries, not interchangeable production baselines. Surrogate errors exceed reference uncertainty.

The cache-hot, resolved-width/context C++ getter counterpart averages 1.725 ns/query in long loops; the ctypes loop averages 0.567 microseconds/query. All 480 returned vectors are native-validated, and their supplied support knots/values match exactly. Neither number is a measured full-PEX query latency or a single-request P95.

## Fixed-node native deployment

B=8, seed 11; three repetitions on each of eight unchanged layouts. The following ratios compare mean extraction wall time; fidelity uses the same original-rule reference.

| Case | CMI ratio | Binary ratio | Full ratio | Full net-C NRMSE | Full worst-slack delta (ps) |
| --- | ---: | ---: | ---: | ---: | ---: |
| asap7/aes | 1.002 | 1.018 | 1.002 | 0.00494 | +0.082323 |
| asap7/ibex | 1.002 | 1.010 | 0.985 | 0.00505 | +0.043632 |
| gf180/aes | 0.993 | 1.046 | 0.983 | 0.00099 | -0.767708 |
| gf180/ibex | 0.979 | 0.983 | 0.983 | 0.00097 | -1.532078 |
| ihp-sg13g2/aes | 1.007 | 1.002 | 1.017 | 0.00112 | +1.075149 |
| ihp-sg13g2/ibex | 0.988 | 0.977 | 1.020 | 0.00111 | +2.630785 |
| sky130hs/aes | 1.024 | 1.001 | 1.020 | 0.00071 | -0.038636 |
| sky130hs/ibex | 1.005 | 1.000 | 1.047 | 0.00054 | -0.294000 |

Shared input, model-bundle and support preparation costs 0.877 s once in this comparison pipeline. The measured reuse is two designs per process, eight total. Predict/export and marginal totals are in deployment_cost.json. All electrical SPEF sections match the frozen corresponding variants. Rule registration only stores a filename; parse time remains inside extraction. Rule-only allocation and isolated parse latency are not claimed.

## Cost and completion levels

Main measured execution: 0.6489 CPU core-hours. With a conservative 0.25 core-hour auxiliary allowance, budget charge is 0.8989, below the 8 core-hour scope. No GPU or source training was run. Supplied characterization and selected source-stage receipts are separately listed in supplied_input_costs.json; they are not zero-cost lifecycle claims.

- **query_level_replay**: completed: 71 template geometries and 480 native replay geometries, Q limits 1/8/32.
- **independent_reference**: completed: 213 resident one-RHS solves of the same 71 certified fine templates.
- **fixed_node_offline_export**: completed: 12 identical rule exports; 96 release native extraction/STA runs.
- **offline_rule_enrichment**: new rule nodes NOT implemented or claimed.
- **actual_online_substitution**: NOT implemented or claimed.
- **native_FEM_physical_alignment**: NOT established; native agreement and template physical error remain separate.
- **exact_full_layout_cross_sections**: NOT claimed; the physical contract is a symmetric 2D layout-parameterized template.
