Fig. 4 Ungated trial (not applied to the formal manuscript)

Open main_ungated.pdf to review the trial paper, or coverage_four_ratios_ungated.pdf/png for the isolated figure.
The formal main.tex, main.pdf, references, and coverage_four_ratios.pdf/png remain untouched.
Rollback: keep using ../../main.pdf. No restore, checkout, or reset is required.
The baseline directory contains the pre-trial source, PDF, figure, and SHA-256 hashes.

Data protocol:
- Exact original Fig. 4 common-feasibility support/query episodes, all three domains and all four holdouts.
- Reuse frozen three-member Ungated 30% accumulators; evaluate the same frozen checkpoints at 10/50/70%, without training.
- Match every support/query hash, segment's scored indices, and squared truth against the original coverage records.
- Use the same pooled process/family/component, then mean-mask NRMSE aggregation.
- Existing four series are copied without changing any value; purple dash-dot diamond markers denote Ungated.
- The original same-holdout protocol is unchanged; budgets or different query populations are never substituted.

Files:
  build_trial.py, reproduce.sh: isolated runnable entry points.
  ungated_*.jsonl.gz: raw per-episode/segment accumulators and support/query identities.
  *_receipt.json: checkpoint/input hashes, inference counts, and evaluation resource usage.
  plotted_scores.csv: all five plotted series.
  aggregation_checks.json: reproduction of the original Full summary from raw records.

Reproduce from the repository's existing environment/checkpoints:
  bash <this-directory>/reproduce.sh
Completed domain outputs are reused only after raw-hash validation. No production summarizer is invoked.
The trial source changes only the Fig. 4 image path and its three-member caption.
