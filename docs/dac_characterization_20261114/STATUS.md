# Completed local delivery

End state: **COMPLETION_ACCURACY_ONLY**. Stages A/B and the bounded E1–E4 matrix are complete. No training, native extraction, solver or GPU job remains queued for this study. No remote push, release or submission was performed.

Original repository HEAD and fetched origin were 05d0717c31c3ebd38107c846cfa7712913078027. Original checkout, original manuscript/PDF, catalog data and full/control weights remain unchanged. Worktree: `../dac-capacitance-20261114`; branch: `research/dac-capacitance-characterization-20261114`. Initial audit/protocol commit: 1486537. Use `git log` for the delivery and verification commits; the verification receipt identifies the implementation commit it checked.

Completed evidence:

- Main public/FEM/transfer confirmation: 32,448 / 3,840 / 1,920 records, zero scientific execution failures. Adapted official AttentionCap adds 720 records. Reverse direct MLP adds 240 records. Three-member gate sensitivity adds 7,164 records.
- All 18 existing controls were verified and reused. New source training: 24 MLP/CNP, 8 adapted AttentionCap and 4 reverse-MLP runs. No control retraining and no new FEM solves.
- 120 exported rule files; eight golden native replays and 240 budget native evaluations, all complete. Golden C/R are exact; candidate R and inputs are fixed. Native full improves over CMI in all 16 layout/budget mean cells, but improves over binary in only 6/16 net-C and 4/16 WS cells.
- Final adapter/label-isolation, budget/cache, fixed-Q, learned-baseline and 600 overlapping export/score episode checks passed. Geometry cost index covers 12,024 geometries; the trajectory ledger records 38,160 unique purchases. The 2,728 native output artifacts have a separate complete hash index.
- Archived invalid fork attempt and one native administrative handoff are retained with costs and limitations. Historical fixed-mask negative results remain separate from new budgets.

Decision: retain a bounded rule-completion/engineering claim. At the frozen middle threshold full requires less recorded target work than its own anchor, but matches the budgets of adapted MLP and binary in the FEM/transfer cohorts; it is not generally necessary or more characterization-efficient than strong controls. No actual solver wall-speedup or total amortized cost advantage is established. The editable paper states this result and does not recommend immediate submission on the broader efficiency claim.

Delivery map: [DELIVERY.md](DELIVERY.md). Verification or report rebuild: `bash experiments/dac_characterization_20261114/reproduce.sh verify` or `report`, from the research worktree. No scientific rerun is needed. Large local raw/native files and new weights are preserved outside Git with hashes; raw compressed evaluations, cost ledgers, figures, configs and manuscripts are versioned. Missing external files on another machine require the documented asset transfer/retraining procedure, not replacement by old score CSVs.
