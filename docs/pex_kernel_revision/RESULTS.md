# Completed PEX kernel and compute-table results

Continuation of `a519539fee8a763c74e1db61427fdd02d85511ca`. Main PDF: 6 pages; expanded PDF: 15 pages.

## Shared physical support

| Method | NRMSE | P95 absolute (pF/m) |
|---|---:|---:|
| mli | 0.00452 | 0.240 |
| openrcx_ideal | 0.00635 | 0.704 |
| openrcx_kernel | 0.01072 | 0.799 |
| anchor | 0.00451 | 0.240 |
| binary | 0.02218 | 1.337 |
| full | 0.01675 | 1.024 |
| binary_compute | 0.02901 | 1.473 |
| full_compute | 0.02447 | 1.554 |

The same 71 full-support templates are independently referenced, not exact arbitrary layout sections. Native width mapping is retained in both OpenRCX variants; the ideal variant removes distance quantization only. Direct learned queries and whole-slot generation have distinct Q protocols. Full populated-table error exceeds the native kernel on this cohort. No query-error-selected fallback hides that result.

## Coverage and native deployment

All 21,840 shared-support/query episodes cover the complete 10/30/50/70% sweep. Full/Binary 30% scores match their prior results exactly. The source-selected numerical GP and actual anchor remain controls. Complete-cell MLI, sparse/boundary extensions, actual support counts and rounded duplicate episodes are separately recorded.

The new internal interface prepares 49,657 slots. Native-value pass-through preserves getters and electrical SPEF; learned returns match payloads, resistance and uncovered returns are unchanged. The 120 release runs cover all eight layouts, five modes and three repetitions. Full extraction ratios range 0.991–1.035; first-design PEX overhead including explicit preparation is 161.1–670.4%. This is separate from the existing fixed-node 0.983–1.047 result.

| Layout | Full extraction ratio | Full net-C NRMSE | Worst-slack delta (ps) | Cold PEX overhead |
|---|---:|---:|---:|---:|
| asap7/aes | 0.991 | 0.00426 | +0.1733 | 233.3% |
| asap7/ibex | 1.020 | 0.00516 | +0.5101 | 161.1% |
| gf180/aes | 1.031 | 0.00030 | +0.1676 | 319.9% |
| gf180/ibex | 0.999 | 0.00020 | +0.2050 | 281.8% |
| ihp-sg13g2/aes | 1.035 | 0.05656 | +74.4143 | 670.4% |
| ihp-sg13g2/ibex | 1.029 | 0.05477 | +147.4394 | 444.9% |
| sky130hs/aes | 1.017 | 0.00382 | +2.2757 | 330.4% |
| sky130hs/ibex | 1.024 | 0.00233 | +2.3919 | 314.2% |

Cold per-library numbers include a full model load and the inventory extraction required by deferred rule loading. Process residual includes startup/payload parsing and shutdown. SPEF and STA are separate, not denominators used to dilute PEX overhead. Small ratios below 1 are not claimed stable speedups. Native reference error is fidelity, not independent electrostatic error.

New measured compute: 2.100 CPU core-hours; conservative auxiliary allowance 0.50; total charge 2.600<16. No new source training, GPU, or physical reference solves.

## Completion levels

- **production_kernel_comparison**: completed: pinned extracted OpenRCX function bodies plus specified MLI; no commercial binary execution.
- **same_physical_reference**: completed: 71 full-support symmetric 2D templates, including learned slot generation and native retrieval.
- **coverage_sensitivity**: completed: 21,840 paired episodes, 10/30/50/70%, all intended domains/conditions.
- **compute_table_injection**: completed: original/disabled/native pass-through/Binary/Full; full original rules unchanged.
- **grid_reuse**: completed: whole eligible grids identical across two designs/process.
- **fixed_node_export**: separate completed B8 path reused from runtime_accuracy_20261115.
- **online_neural_inference**: not implemented; inference occurs during preparation.
- **native_calibration_to_FEM_alignment**: not claimed; native fidelity and template physics separate.
- **commercial_xRC**: not run; supplied core mathematics only.
