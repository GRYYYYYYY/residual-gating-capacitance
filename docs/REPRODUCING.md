# Reproduction levels

Run from the repository root after installing the package in a fresh environment. Download only the packages needed by your level. Versions used for the portable validation are pinned in `requirements-validated.txt`. Original per-run receipts retain the training configuration and numerical evidence; the release makes no claim that a different library version produces identical retraining trajectories.

## 1. Data and numerical provenance

`python -m capdata fetch database` installs the original public tables, the downstream-held-out view, three generations of generated FEM tables/matrices, geometry contracts and fixed cohorts. `python -m capdata verify --package database` verifies every member.

Reference matrix joins are `table_id -> grid.reference_id`, preserving each table's grid order and verifying coordinates, then `grid.id -> matrix.id`. Do not count transfer/cross-fit views or coarse/wide variants as new independent labels. The original reference has 32x153 matrices; Round 2 has 24x153; Round 3 has 27x128. The public confirmation file has 341 rows but 340 unique scored tables after `pdkcap.train.unique_tables`.

To reconstruct the public inventory independently from pinned network sources into a NEW directory:

```bash
python scripts/prepare_public_inputs.py --output results/public_reconstructed
```

The downloader verifies all 51 source hashes and the exact original table-file hash. To rebuild the 84-table holdout view, use `scripts/build_holdout_split.py` in a fresh installation without an existing holdout output; it refuses overwriting. That derivation also uses the released upstream table inventory and original in-domain split under `upstream/data/`.

## 2. Fresh inference and scoring

```bash
python -m capdata fetch database models
python scripts/inference_demo.py --domain public
python scripts/inference_demo.py --domain reference
python scripts/inference_demo.py --domain to_asap7
python scripts/inference_demo.py --domain to_freepdk15
```

These commands each score ONE deterministic held-out episode. They test loading and inference, not paper-level aggregates. Four-domain exact original-vs-portable prediction parity is recorded in `results/inference_parity.json`.

Full reference confirmation scoring, into a new run:

```bash
python -m unified.score \
  --cohort runs/round3_evaluation_inputs_v1/reference_confirmation_round3_main.jsonl \
  --checkpoint runs/v10_reference_all_s0/checkpoint.pt runs/v10_reference_all_s1/checkpoint.pt runs/v10_reference_all_s2/checkpoint.pt \
  --output reproduced_reference_confirmation --method v10_all --workers 4
```

For the public domain use the three `holdout_g_s*` checkpoints and `public_retrospective_original.jsonl`, not the old `g16` selection. `configs/selected_models.json` is the authoritative mapping for all domains.

## 3. Recorded table/figure reproduction

```bash
python -m capdata fetch database experiment-records sta-visualization
python scripts/reproduce_reports.py --sta --output results/my_reproduction
```

This recomputes the reported aggregation from recorded predictions and measurements. It verifies all 39 tables, writes new figure outputs and does not rerun latency benchmarks, training or FEM solves. Individual entry points: `analysis/build_tables.py --regimes`, `analysis/build_tables_v3.py`, and `analysis/sta/analyze_plot.py CASE_DIRECTORY`. Copy a case's `raw/` and `provenance.json` to a fresh directory before invoking the plotting script to preserve downloaded artifacts.

## 4. Retraining

Stage-1 and stage-2 commands are available in `scripts/train_stage1.py` and `unified.train`. Each run refuses to overwrite an existing run. For example, public seed 0:

```bash
python scripts/train_stage1.py --data runs/public_inventory_holdout_v1/tables.jsonl \
  --output my_holdout_stage1_s0 --seed 0 --steps 2000 --eta 0
python -m unified.train --help
```

Use the exact arguments in `runs/holdout_g_s0/FROZEN.json` for the stage-2 configuration, replacing the output and stage-1 checkpoint names. The public headline uses 24,000 stage-2 steps. The reference/transfer headline uses 12,000 steps and the original three-seed initialization sets now included in the model package. Configurations, scales and initialization hashes are preserved; the release does not silently substitute newly initialized networks for those recorded initializations. Historical `scripts/train_all.sh` and selection drivers are retained for provenance, but use the selected-model mapping and run-specific receipts for the current headline configuration.

## 5. Exact saved-layout STA replay

```bash
python -m capdata fetch sta-layouts
python scripts/fetch_sta_libraries.py --platform gf180
python scripts/replay_sta.py --case gf180/ibex --missing 50 \
  --openroad /path/to/openroad --outdir results/my_sta_replay
```

Use OpenROAD `0b54bb3203e0895f87940ff982358a6e4d406e28` (reported as `26Q3-1860-g0b54bb3203`) and ORFS `19480a228f583dcb2fc8f4bd6427dbab5253bc70`. The ODB format is version-sensitive. Executables are installed separately; the Liberty/RC downloader pins both URLs and hashes. `database/sta_cases.json` indexes all eight cases, the original routed and connected ODBs, SDCs and 104 SPEFs. The replay reads the same connected ODB/SDC and changes only SPEF, checking resulting WS/TNS against each archived value. It does not reroute or change timing constraints. Native STA time units differ by platform; archived values and replay assertions use the platform's native unit, while published visualization CSVs are ns.

The rule-export/re-extraction code is preserved in `scripts/downstream_holdout_*.py` and `scripts/upstream/`; this older orchestration assumes an ORFS workspace under `RG_UPSTREAM_ROOT`. The saved-layout replay above is the tested portable entry point. Fresh synthesis/routing would be a new layout and must not be labeled an exact reproduction of these saved cases.

## 6. FEM generation and numerical evidence

```bash
python -m capdata fetch numerical-evidence
pip install -e '.[solver]'
python scripts/fetch_reference_inputs.py --output upstream/ctf
```

The last command obtains exact original material inputs; it does not grant upstream redistribution rights. Set `RG_CTF_ROOT` if stored elsewhere. Generated geometry grids and contracts are in `runs/reference_design_v2`, `runs/round2_design_v2`, `runs/round3_design_v1`. Numerical evidence archives retain original per-solve specs, results, logs and frozen source snapshots; use each generation's snapshot and gates when regenerating it. `solver/fem.py` and `pdkcap/solver_worker.py` expose the numerical implementation, and `pdkcap.bulk` / `pdkcap.round3_bulk` provide budget-aware batch runners.

Those historical batch runners require an explicit local compute-budget file; no old authorization is silently reissued by downloading this repository. Normal data use, scoring and plotting need no solver rerun. Coarse/fine/wide differences are convergence evidence, not independent training examples, and saved matrices are neither clipped nor symmetrized.
