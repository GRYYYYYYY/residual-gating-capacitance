# Repair and resume record

Start HEAD: `449fa39556ef9803d8e5eda14ec330324cb3383b`; clean worktree on `research/dac-capacitance-characterization-20261114`. Prior failed attempt, reports, raw logs, paper and archive remain unchanged. The latest explicit instruction replaces its one-repair limit with bounded engineering repair (900 additional CPU seconds inside the unchanged cumulative 14,400 seconds). No completed scientific endpoints existed at the start.

## Engineering changes

- All new execution scripts share `ATTEMPT.json` through `paths.py`; budget, model, stage receipts and reports use the same attempt identity and new results/docs paths.
- The exact raw-encoding comparator checks finite numerical fields, identical boolean validity masks and shapes, finite and exactly equal applicable delta entries, and NaN at every unavailable raw delta entry. It does not relax numerical tolerance, accept common applicable NaNs/Inf, or apply raw NaN semantics to padded/stacked tensors.
- Existing explicit Python-int support-index conversion is retained. Preparation regenerates the identical sampler/geometry ordering, validates a JSON round trip and compares full semantic episode content against the previous attempt (gzip metadata need not match).
- `PREFLIGHT.json` explicitly denotes partial checks. Only complete successful preparation atomically publishes `PREPARE_SUCCESS.json` with artifact/source hashes. Freeze verifies that receipt and loaded table hashes; only complete manifest publication can lead to `FREEZE_SUCCESS.json`.
- Driver stages run with checked return codes. The same gate functions are called in freeze, pilot, formal workers and evaluation. Missing/altered success receipts refuse downstream work. Formal workers require `FEASIBILITY_PASS` bound to the same freeze and four pilot receipts/states. Evaluation checks all 12 final checkpoint hashes, final step and freeze identity.
- Full and binary complete pretrained states remain their respective initial states; AdamW resets equally in H/L. Seed0's 20-step pilot prefixes preserve model, optimizer, RNG and step and resume at 20, with exactly 2000 total updates. Other seeds start at 0. No checkpoint selection on validation or confirmation outcomes.
- Actual source/confirmation table content is verified at worker/evaluator entry, not merely by hashing a manifest. Six source weights, their configs/receipts and actual Python dependencies are bound to the successful freeze.

## Unchanged scientific design

One FEM reference setting, 16 source tables ×153 nodes, Full/binary × H/L × original seeds0/1/2, 2000 updates, AdamW lr2e-4/wd1e-4, clip1, all parameters, dropout0, normalized Huber delta1, eta0/four equal family weights, no span weighting. H retains its original sampler; L is nested geometry-only thinning with B4/8/16/32 and independent RNG611140+seed. Original H query, truth and loss weights remain paired. No removed supports become additional queries. The resulting intervention changes count and coverage; it does not isolate cardinality alone.

The old 192 low-budget and64 original-support cells, the primary table/group aggregation order, C/D/I/G definitions, and old E1 pooled SSE/SY reconstruction are unchanged. No new target labels, solver jobs, baseline fitting, transfer or native PEX/STA. Results remain retrospective. Global `COMPLETION_ACCURACY_ONLY` is separate from the mechanism outcome.

## Regression and accounting evidence

`REGRESSION_SUCCESS.json` records legitimate inputs passing and common applicable NaN/Inf, zero unavailable sentinels, finite-value/mask/shape changes, nonfinite features, missing stage gates and failed predecessor commands being rejected. Real preparation is a separate gate and must pass; synthetic regression alone is not sufficient.

Prior summary and append-only ledger agree at150.849287 seconds, including the old60-second debit; their hashes are pinned in ATTEMPT.json. No later mechanism ledger or process was found. That amount is carried once. This attempt separately reserves30 seconds for its own light setup/driver bookkeeping/status/final packaging. All actual regression, preparation, freeze, pilot, training, evaluation, statistics and paper generation are measured through the same supervisor. The engineering sub-budget includes its30-second debit. RUSAGE_CHILDREN after wait includes waited descendants; supervisor SELF is separately counted, without double charging child time. Per-job wall and CPU remain separate.

The shell alias `python` was absent during initial file setup; those two setup snippets did not execute and were rerun using system python3. No model computation occurred in those failed shell invocations; lightweight setup is covered by the new administrative debit. No scientific parameter changed.

The successful stage receipts and final mechanism report provide actual outcomes. Old failure reports remain historical, not rewritten as successes. The same session's explicit authorization to push evidence/new paper persists; only the research branch will be pushed, with no main merge, publication or submission.
