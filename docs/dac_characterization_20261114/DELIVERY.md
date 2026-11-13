# DAC characterization study delivery

Read [FINAL_DECISION.md](FINAL_DECISION.md) first. The final state is **COMPLETION_ACCURACY_ONLY**, with no claim of submission readiness or general characterization efficiency.

| Item | Location from repository root |
|---|---|
| Decision and claim-by-claim evidence | `docs/dac_characterization_20261114/FINAL_DECISION.md`, `CLAIM_EVIDENCE.csv` |
| Audit, scope, fairness and related-work limitations | `docs/dac_characterization_20261114/` |
| Frozen protocol and complete input/model hashes | `experiments/dac_characterization_20261114/EXPERIMENT_PLAN.yaml`, `MANIFEST.json`, `selected_*.json` |
| Runnable fixed-Q evaluation | `experiments/dac_characterization_20261114/evaluate.py` |
| Verification/report entry | `bash experiments/dac_characterization_20261114/reproduce.sh verify` or `report` |
| Main and adapted-baseline raw predictions, S/Q and costs | `results/dac_characterization_20261114/confirmation_*/records.jsonl.gz`, `attention/*_confirmation/records.jsonl.gz` |
| Unique geometry purchases and original solver work | `results/dac_characterization_20261114/query_charge_ledger.csv`, `geometry_cost_index.csv` |
| Per-method and source/target/native cost tables | `results/dac_characterization_20261114/summary/cost_ledger.csv`, `training_cost.csv`, `native_cost.csv`, `resource_usage_summary.json` |
| Curves, paired statistics, censoring and all downstream metrics | `results/dac_characterization_20261114/summary/` |
| Reproducible PDF/PNG figures | same summary directory: `budget_accuracy`, `fixed_error_cost`, `completion_cost`, `gating_training_seeds`, `native_fidelity_B4`, `workflow`, `architecture` |
| Editable research manuscript and compiled review PDF | `paper/dac_revision_20261114/DAC_REWRITE.md`, `main.tex`, `main.pdf` |
| Local native inputs/results and export rules | `results/dac_characterization_20261114/downstream/native/`, `downstream/rules/` |
| Large local artifact index | `results/dac_characterization_20261114/summary/native_artifact_manifest.json`, `docs/dac_characterization_20261114/DELIVERY_MANIFEST.json` |
| Final verification and preservation checks | `docs/dac_characterization_20261114/FINAL_VERIFICATION.json`, `results/dac_characterization_20261114/preservation_verification.json` |

All links are local/repository artifacts; nothing was published. Native outputs and 36 new local weight files are retained but ignored by Git. The roughly 7.8 GB result tree remains below the frozen 15 GB ceiling. The resource summary separates CPU measurements, sums of invocation walls, and unknown costs. It does not infer native CPU from wall time or claim a fully measured end-to-end total.

The paper is a complete editable research revision in a compilable local article layout, not a verified current DAC submission template. Remaining evidence gaps are substantive: two-dimensional numerical physics, only two transfer stacks, previously inspected confirmation cohorts, modified AttentionCap supervision, an imbalanced and shorter-trained new public MLP/CNP control, and missing full source/amortized costs. No extra model sweep or solver campaign is launched to force a positive result.
