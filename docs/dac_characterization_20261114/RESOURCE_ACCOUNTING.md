# Resource accounting

The frozen ceiling is 32 new CPU-hours, 15 GB new artifacts, four heavy CPU jobs, one thread/job, zero new GPU allocation and zero new solver jobs. Top-level training/evaluation batches and their child native invocations are separate counts. The native matrix was fixed at 8 golden plus 240 candidate invocations, even though the top-level-job estimate in the original plan was 55. Nothing expands the scientific matrix.

- New source MLP/CNP training: 24 runs (two LR candidates at seed0, selected LR seeds1/2, two models, three settings).
- Adapted AttentionCap: 8 runs (same finite LR/seed rule, two settings).
- Reverse direct MLP: 4 runs, limited to source ASAP7 / target FreePDK15.
- Full/residual/binary original members: all reused, no new training.
- FEM solves: none. Historical 12024 geometries, with 3 numerical levels, are a cost replay only.
- Target adaptation is executed independently for each S and ensemble member, charged in the raw completion/adaptation timing; it is not an uncharged cached target fit.
- Training wall/CPU receipts are in training_cost.csv. Reverse training only records wall, so CPU is unknown rather than zero. Full/warm-start/control historical receipts are separate, with missing CPU/GPU fields unknown.
- The invalid public fork worker consumed 770.07 CPU seconds; this remains a failed-execution debit. It produced zero accepted result rows. Its orchestration repair did not change scientific settings.
- Native handoff preserved every child task/output. One reconstructed wall duration is labeled in its receipt; original extraction timings remain measured. Native process CPU totals are not inferred from wall time.

Source-characterization costs by fitting/selection view are in source_characterization_cost.json. These overlapping views must not be added as independent data. fine-only and coarse+fine+wide validated costs remain distinct. query_charge_ledger.csv records each first purchase along a sampling trajectory; cumulative budget snapshots and multiple methods sharing S are not additional paid geometry queries. Public queries are only simulated row accesses.

No sum of CPU seconds, GPU hours and shared-host wall time is presented as an end-to-end runtime. No new paid infrastructure was requested, and unrelated pre-existing simulations remained running.
