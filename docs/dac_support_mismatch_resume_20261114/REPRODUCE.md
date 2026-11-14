# Reproduction

Start HEAD:449fa39556ef9803d8e5eda14ec330324cb3383b. Research worktree: `/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114`. Original failed results remain under `results/dac_support_mismatch_20261114/` and must not be deleted or relabelled.

## Actual execution

```sh
source experiments/dac_characterization_20261114/env.sh
"$DAC_PYTHON" experiments/dac_support_mismatch_resume_20261114/driver.py \
  > results/dac_support_mismatch_resume_20261114/driver.log 2>&1
```

The driver runs regression → prepare → freeze → four seed0 pilots → feasibility → twelve final continuations → fixed evaluation. Each subprocess is checked before the next can launch. All compute is wrapped by the shared budget supervisor, single-thread and single-worker, GPU disabled. Default launch is exclusive: a completed attempt cannot be silently rerun into the same files. A new independent reproduction requires a new explicitly configured attempt and its own authorized resource accounting; do not reset or overwrite the cumulative ledger of this execution.

The literal original sources,16 source training tables,24 validation tables and16 confirmation tables remain read-only. `CHECKPOINT_LINEAGE.json` references six actual source weights/configs/receipts. `DATA_MANIFEST.json` pins canonical loaded-table content; each training/evaluation entry rechecks that content. `FREEZE_MANIFEST.json` covers executed scientific sources, actual imported pdkcap/unified modules, common.py, paths.json, paper_models.json, source configs/data/checkpoints and the paired episode/evaluation plans. The manifest is a code/worktree snapshot even if its Git parent precedes the repair commit. `FREEZE_SUCCESS` binds it to complete preparation.

`EPISODE_PROVENANCE.json` gives old/new compressed file hashes and a shared semantic-content hash. Gzip metadata differences do not change scientific episodes. The original sampler is restarted at each fixedseed for the additional training, as preregistered; H does not restore the historical optimizer/RNG trajectory. L changes support count and coverage inside the same H pool, never the query loss population.

The four20-step seed0 prefixes are saved with full model/optimizer/RNG/step. `FEASIBILITY_PASS` binds all four states and the freeze. Formal seed0 workers must start at20; other seeds at0; all end at2000. `ENDPOINT_COSTS.csv` and per-member `COMPLETED.json` prove final steps and weight hashes. Large `.pt` files remain local and are path/hash referenced. Do not replace a missing final checkpoint with a pilot state.

## Evaluation and derivation

The existing fixed S/Q low-budget192 cells and original-support64 cells are unconditionally evaluated for all six source members and twelve final members. EVALUATION_CELLS stores per-component SSE/SY, absolute errors and query counts, permitting the historical pooled metric to be reconstructed separately from the frozen new table/group metric. Raw PREDICTIONS.jsonl.gz and PREDICTION_TIMING.csv retain exact outputs and stage timing. They are not repeated solver measurements.

After the driver succeeds:

```sh
"$DAC_PYTHON" experiments/dac_support_mismatch_resume_20261114/budget.py analysis analysis \
  "$DAC_PYTHON" experiments/dac_support_mismatch_resume_20261114/analyze.py
"$DAC_PYTHON" experiments/dac_support_mismatch_resume_20261114/budget.py delivery report \
  "$DAC_PYTHON" experiments/dac_support_mismatch_resume_20261114/report.py
```

The analysis source is hashed before endpoint evaluation. All three seeds, four budgets, component/table/group effects, original-support retention, tails, timing and old pooled aggregation are preserved. Bootstrap uses2000 replicates/RNG61114, process-stratified dependency groups, keeping all paired cells and the three fixed training seeds together. It is conditional on four groups, not a broad-process inference or independent-ensemble analysis. Old MLP/CNP comparisons are descriptive, with different training opportunities.

`DAC_REWRITE.md` in the new paper directory is the sole main-text source; `render_paper.py PAPER_DIR` generates TeX with the same section order, followed by two pdflatex passes. Old papers remain unchanged. Final SOURCE_OF_TRUTH and PAPER_DELTA document provenance and sentence-level evidence. Scientific plotting uses the exported CSVs, with all seeds visible.

## Accounting and stopping

Prior debit150.849287s includes the original60s conservative administration; it is inherited once. The new attempt has a separately justified30s lightweight-administration debit. Every regression/preparation/failure/pilot/continuation/evaluation/analysis/paper subprocess is measured. Engineering regression/prepare/freeze are additionally limited to900s including the new debit. Total cumulative debit cannot exceed14,400s. The successful pilot feasibility formula is cumulative used +2×slowest pilot CPU/update×23,920 remaining updates +1,800s reserve, with current-stage overhead allowance explicitly added.

RESOURCE_LEDGER is append-only, reporting CPU and wall separately, with waited descendant CPU and supervisor CPU counted once. RESOURCE_SUMMARY combines prior/new measured and conservative totals. Review ZIP includes hashes/file inventory and lightweight outputs; large raw prediction/weight files are referenced. Completed12-member evaluation and delivery end the run; no new research search is triggered. Current session explicitly authorizes pushing the research branch; no main merge or submission.

Presentation-only finalization: presentation.py regenerates the paired-effect chart from the same CSVs with a shorter unclipped axis label and recompiles the unchanged TeX. Original plot/PDF and receipt remain under presentation_original; PAPER_FINAL_SUCCESS binds the final PDF. This changes no numerical values, metrics or parameters.
