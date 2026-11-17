# Reproduction

Run from the specified repository root:

```bash
bash scripts/dac_main13_integrated_revision/reproduce.sh --summaries
bash scripts/dac_main13_integrated_revision/reproduce.sh --verify-contracts
```

The first recomputes original Fig.4 statistics, strong-control figures, independent
paired statistics, trace accounting, completed native/mechanism tables, then builds
the single main.tex. It requires finished raw receipts; it does not retrain or claim
completion from script existence. The second reexecutes poison-derived predictions
and checks all24 sparse input/payload contracts. Candidate diagnostics are scored
independently by `score_candidates.py`, only after all frozen output receipts exist.

Full experimental reproduction is deliberately exclusive-create:
`reproduce.sh --clean-experiment` refuses an existing output directory. Use a
separate checkout with the same archived dependencies and an empty experiment
output; do not delete or rename completed evidence to force a rerun. The training
queue uses three CPU workers and the native/post-native chain one, with one thread
each. Budgets and failure boundaries are in protocol.yaml. A failed/incomplete
attempt must be archived and diagnosed; there is no automatic performance retry.

The source environment is experiments/dac_characterization_20261114/env.sh.
Existing runs/ is an external archive symlink. Configured source checkpoints,
source-only training/selection data, confirmation records, OpenROAD binaries,
routed ODBs, libraries and SDCs must remain available. Exact hashes are in
results/dac_main13_integrated_revision/main13_20261117/dependency_manifest.json,
coverage_checks.json, per-run native receipts and training FROZEN/COMPLETED files.
Original sources/results/models are read-only; the paper snapshot location is
recorded in snapshot.json. No internet or GPU access is required by these commands.

Three distinct protocols are never merged: rule-export budget studies, archived
full-characterization compute-table studies, and the new sparse-native matrix.
The raw native outputs include SPEF, endpoint TSV, logs, comparisons and stage
receipts. Candidate outputs precede independent scoring and retain every member,
query, mask, weight and support descriptor. Reproduce interval estimates at the
recorded independent-group level, not by treating queries or seeds as independent.

The first evidence-backed text edit is revise_paper.py, which applies exclusively
to the original main13 snapshot and should not be rerun on an already edited paper.
Subsequent generated tables are inputs to the same formal main.tex. The snapshot
is an archive, not a second maintained manuscript.

The final source lineage audit includes the2k-step source residual initializers
in addition to the24k/12k fusion stages. Historical FEM/Transfer byte hashes
resolve under the recorded solver_root; released copies differ only in
reference_contract metadata. Coordinates, labels and partitions are identical.

Additional derived-entry scripts are additional_summaries.py (paired native seed
ranges/process-cluster intervals, reuse models and retained numerical controls),
mechanism_interpretation.py (independently scored cases and MLI status reconciliation),
check_candidate_contract.py (all65520 member-episode gate algebra checks), and
verify_originals.py (snapshot comparison with unchanged-file fingerprint reuse).
The final report renderer runs only after experiment receipts pass, and the
manifest gate checks the actual PDF compile log and source/result preservation.

Old MLI status counts are preserved in coverage_checks.json. The corrected status
mapping and unchanged error replay are in mli_status_reconciliation.json and
mli_status_reclassification.csv. No old raw inventory is rewritten.

All reported cold/reuse totals are sums/models of measured stages. External
Python startup/imports are unmeasured, while native-process residual is included
where stated. Native-sparse has a separately measured warm-cache input-release
cost and no injection inventory/model-loading requirement. --verify-contracts
preserves the first input-release timing file rather than replacing it.

The native coverage CSV separates eligible/populated/changed/unchanged and
unpopulated/excluded grid slots for all192 arm-settings. Grid slots are not
getter calls; fallback/uncovered return counts are measured only in the two
smoke traces. Their raw per-arm counts are preserved in native/smoke_pass.json.

The delivered PDF has an explicit human visual-review receipt. A regenerated PDF
with a different SHA256 must be reviewed again; finalization reports that separate
status as NOT_RUN until a matching review exists. Automatic compilation checks
never fabricate a human review.
