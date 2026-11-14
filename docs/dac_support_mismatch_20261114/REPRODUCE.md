# Reproduction and status

Start commit: b0a2edcac216af53b417be2a3b922c4deff98185. Worktree: /inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/opensource_release/dac-capacitance-20261114. Branch: research/dac-capacitance-characterization-20261114.

This is a reproducible **failed preflight**, not a working completed training run. Do not run worker.py or evaluate.py on these artifacts: FREEZE_MANIFEST.json is absent, the frozen gate fails closed, and the one-repair policy stopped the run. Existing files use exclusive creation; reproduction requires a fresh results directory in a separate worktree, preserving this evidence. Paths to six source weights and hashes are in SOURCE_WEIGHT_MANIFEST.csv. Data installation is the existing read-only runs symlink. Environment comes from experiments/dac_characterization_20261114/env.sh; exact interpreter and CPU measurements are in RESOURCE_LEDGER, runtime versions in ENVIRONMENT.json. Zero GPU/new solver/native runs.

Actual invocation prefix (all substantive compute is budgeted):

```sh
source experiments/dac_characterization_20261114/env.sh
"$DAC_PYTHON" experiments/dac_support_mismatch_20261114/budget.py JOB "$DAC_PYTHON" experiments/dac_support_mismatch_20261114/SCRIPT.py
```

Recorded jobs: prepare → failed numpy.int64 serialization; prepare_repaired → failed NaN-unaware delta equality; freeze → failed because prepare had not produced DATA_MANIFEST; diagnose → read-only semantic check; build_delivery → documentation/NA tables/separate editable manuscript and PDF, with children explicitly waited. Exact executed commands are retained in RESOURCE_LEDGER.jsonl. The original pre-repair prepare.py is reconstructed by undoing the single int conversion; a copy is archived in invalid_prepare for direct audit.

No pilot, worker continuation, endpoint prediction, bootstrap or plotting command ran. Empty numerical outputs are intentional and explicitly labelled. FROZEN_PLAN records the proposed U=2000 design and metric; it is not a successfully finalized freeze. The EVALUATION_PLAN records intended old S/Q only. Do not treat the historical source weights or old fixed-mask scores as new low-budget training outcomes.

Budget cap 14,400 CPU seconds. RESOURCE_SUMMARY distinguishes measured child/supervisor CPU, the 60-second conservative administrative debit, worker-wall sum and overall elapsed wall. Scientific stages are measured via getrusage with single-owner locking; all failures count. The bounded diagnostics can be replayed without training. Re-running the entire intended factorial requires separate authorization and fixing the described harness/ordering defects; no claim is made that it completed within the cap.

Old main.pdf and REVIEW_PACKET are preserved; new paper compilation uses pdflatex twice, with logs and return codes checked. The lightweight ZIP contains a SHA256SUMS manifest. Large raw data/checkpoints are path/hash references only. The final delivery commit SHA and remote branch are reported separately so the archive does not claim to contain its own future Git object ID.
