# Final-paper supplementary controls

These are the matched-budget controls and unclamped numerical extrapolation control in Appendix E. All included scores come from completed experiments; no placeholder or synthetic results are used. This is a supplementary comparison on the existing confirmation cohorts, not a newly blinded test.

## Methods and budgets

- **Ungated residual Transformer:** the same tokenizer, encoder and residual head, predicting `max(0, anchor + residual)` without a gate or analytic branch bank.
- **Binary gate:** the same encoder/residual head plus component-wise anchor/raw-neural gating, using hidden state and support features without analytic-branch agreement statistics.
- **Local affine:** nearest-support affine regression in independent support-normalized coordinates, unpenalized intercept, slope ridge 1e-8, nonnegative outputs, exact observation retention, and no endpoint clamping. Neighborhoods 2/4/8/16 are selected on validation only; selected values are 4 (public), 8 (FEM), 8 (transfer).
- Each learned variant uses the full member's fitting pool, 2,000-step residual warm start, seed, sampler, optimizer, loss and three-member ensemble. Public stage 2 has 24,000 updates; FEM and transfer have 12,000. Full-model scores replay the original reported ensembles.
- Evaluation uses 30% missingness, random/block/extrapolation masks and five mask seeds. The same support partition, scored queries and macro NRMSE recipe are used. `alignment_checks.json` records zero NRMSE difference for the replayed full model.

## Included evidence and regeneration

`scores/` contains per-cell squared-error/truth accumulators, control ensemble/member summaries and affine-selection receipts. `comparison_summary.json`, `public_bootstrap.json`, `seed_stability.json`, and `control_seed_scores.csv` retain aggregate and seed-level evidence. No GPU or large release download is required for:

```bash
python scripts/verify_final_paper.py
```

After installing research dependencies and fetching original experiment records, run from the repository root:

```bash
python -m capdata fetch database models experiment-records
python experiments/paper_controls/verify_controls.py
python experiments/paper_controls/verify_alignment.py
python experiments/paper_controls/build_supplement.py
python experiments/paper_controls/bootstrap_controls.py
```

Generated LaTeX appears in `experiments/paper_controls/generated/tables/`; the checked-in manuscript is never overwritten. Compare `supp_matched_controls.tex`, `supp_affine_control.tex`, and `supp_control_bootstrap.tex` with `paper/tables/`. Paired intervals use 2,000 public-group bootstrap replicates and are pointwise, not simultaneous or uncertainty over training randomness.

## Fresh training/scoring

Use a NEW output root, preserving the released evidence:

```bash
export RG_CONTROL_ROOT="$PWD/results/my_controls"
python experiments/paper_controls/run_controls.py --domain public --variant residual --seed 0
```

Repeat for `public`, `reference`, `to_asap7`, both `residual` and `binary`, and seeds 0/1/2 (18 runs). Full-model inputs are read from the existing release; set `RG_DATA_ROOT` for an external installation. Then, for each setting:

```bash
python experiments/paper_controls/score_controls.py --domain public --kind learned --workers 2
python experiments/paper_controls/score_controls.py --domain public --kind affine --workers 2
```

The three full-model members are replayed during learned scoring. These control checkpoints must be loaded with `SimpleControl` and their recorded variant, not the original full-model loader. Original control checkpoint binaries are not included; fresh-training commands and original per-cell/seed results are supplied. Training and record creation refuse overwriting existing runs. The provided `--smoke` option runs two updates to check execution, not to reproduce scientific results.
