# Residual Gating for Sparse Capacitance Tables

Research code, managed databases, trained models and reproducibility artifacts for **Residual Gating for Sparse Capacitance Tables: One Network that Brackets, Extrapolates and Transfers**. This public release corresponds to the current `paper_v5` experiment snapshot. The manuscript, submission templates, review documents and manuscript ZIP/PDF are intentionally excluded.

[中文使用说明](docs/QUICKSTART_ZH.md) · [数据库总目录](docs/DATABASES_ZH.md) · [Reproduction guide](docs/REPRODUCING.md) · [Versioned downloads](https://github.com/GRYYYYYYY/residual-gating-capacitance/releases/tag/v1.0.0) · [Third-party licenses](THIRD_PARTY.md)

The estimator adds an attention-gated mixture of classical and learned corrections to each table's own interpolation anchor. Evaluation separates in-table interpolation, out-of-table extrapolation and source-only transfer. Public labels are extraction-rule values; generated reference labels are declared 2-D FEM solutions. They must not be merged or described as foundry signoff truth.

## Install

Python 3.10 or newer. Use a fresh environment and an editable source checkout:

```bash
git clone https://github.com/GRYYYYYYY/residual-gating-capacitance.git
cd residual-gating-capacitance
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

For CPU-only PyTorch, install its CPU wheel before `pip install -e .`. The versions actually used to validate this release are in `requirements-validated.txt`. Optional FEM regeneration dependencies are installed with `pip install -e '.[solver]'`; Gmsh also needs its system libraries. No training or solver computation runs during installation.

## One interface for the databases

```bash
python -m capdata list
python -m capdata fetch database models
python -m capdata verify --package database
python -m capdata info public_rules_holdout
python scripts/inference_demo.py --domain reference
```

```python
from capdata import load_tables

training = load_tables("public_rules_holdout")  # train only by default
confirmation = load_tables(
    "eval_reference_confirmation_round3_main", partition="confirmation"
)
```

The loader preserves table/source identities, units, target names and split roles. It never silently merges different rule files or treats evaluation views as extra training data. `RG_DATA_ROOT` can point to a separately managed artifact installation. Current runners are supported from a source checkout.

## What is released

| Package | Content |
|---|---|
| `database` | 51 pinned public rule files; 1,713 original public capacitance tables; the 84-table downstream holdout view; 83 generated FEM base tables and 12,024 fine matrices; geometry contracts, fixed cohorts, transfer/cross-fit views and completed rules |
| `models` | 181 checkpoints from the current study, plus 12 earlier initialization checkpoints; all 12 headline model members are explicitly identified |
| `experiment-records` | Current-study training/selection receipts, baseline and model records, accumulators, ablations, latency measurements, downstream comparisons and unsuccessful/incomplete-run evidence |
| `sta-visualization` | Real endpoint/path/coordinate exports, seed-wise CSVs, plots and provenance for gf180/ibex/block50 |
| `sta-layouts` | Eight exact fixed routed designs, ODB/SDC/DEF/netlists and 104 golden/Linear/ours SPEFs across two masks and three seeds |
| `historical-evidence` | Earlier experiment snapshots and training logs; a damaged 21 GB diagnostic log is represented by its tail and an omission record |
| `numerical-evidence` | 36,072 coarse/fine/wide FEM solve results, specifications/logs and solver snapshots; large regenerable mesh intermediates omitted |

Each package has an archive checksum and per-file SHA-256 manifest. Git stores source, compact reports, figures and manifests; large artifacts are **GitHub Release assets**, not Git LFS. All seven packages can be installed with:

```bash
python -m capdata fetch --all
python -m capdata verify --all
```

Downloads need no access to the earlier private repositories. The installer checks every member and refuses unsafe paths or conflicting local files. Numerical evidence is optional for normal inference and creates many small files; download it only when needed. See `database/packages.json` for exact sizes.

Original AttentionCap CTF inputs are not redistributed because no repository-level license was found at the pinned revision. `scripts/fetch_reference_inputs.py` retrieves and verifies them separately. Public rules and PDK/design-derived artifacts retain their BSD/Apache notices; see [THIRD_PARTY.md](THIRD_PARTY.md). No commercial PTF, credentials, tool binaries, installed environment, unrelated study corpus or manuscript is included.

## Reproduce the reported results

```bash
python -m capdata fetch database models experiment-records sta-visualization
python scripts/reproduce_reports.py --sta --output results/my_reproduction
```

This regenerates the **38 original result tables plus the new STA decision table** from recorded measurements. It does not retrain models or claim to rerun every experiment. The inference example and `unified.score` support fresh predictions; full training and fixed-layout STA replay are described in [REPRODUCING.md](docs/REPRODUCING.md).

Validation receipts are in `results/`: original-vs-portable inference parity for four domains, table reproduction, artifact verification and fixed-layout STA checks. Lightweight tests run with `python -m unittest discover -s tests -v` ; an optional GitHub Actions configuration is provided in `docs/ci-smoke.yml`.

## Model and data provenance

`configs/selected_models.json` binds each domain to its exact three checkpoint hashes and evaluation cohort. The public headline model uses the holdout inventory: all 84 rewritten downstream tables are excluded from its training/validation/test inventory. Reference and transfer models remain their original selected ensembles. Earlier public configurations remain as ablation/selection evidence, not replacement headline results.

The original public confirmation JSONL has 341 rows; the experiment's duplicate-aware loader scores 340 unique tables. Original, Round-2 and Round-3 FEM base datasets have 32, 24 and 27 tables respectively. Derived folds/cohorts are views, not additional physical truth. All numerical fields and checkpoint tensor files are preserved; exported text metadata replaces machine-specific source paths with relative provenance paths. Original and exported hashes are separately retained in the member manifests.

The STA addition measures agreement with golden extraction on fixed layouts. It is **not timing closure**. Seed 0 improves endpoint MAE by 55.1%; seed 1 improves full-path Overlap@50 from 0.76 to 1.00; seed 2 slightly worsens MAE despite lower RMSE. Both methods already identify the same worst path in seed 0. All seeds and these exceptions are retained.

## Layout

- `unified/`: residual gating, correction dictionary, encoding, training, scoring and aggregation.
- `pdkcap/`, `openrcbench/`, `solver/`: original project dependencies, rule parsing/export and numerical generation.
- `capdata/`, `database/`: data access, package installation, catalogs and hashes.
- `scripts/`: current experiment and reproduction entry points.
- `analysis/`: result-table and visualization generators, without the manuscript.
- `results/`: reviewable tables, figures and validation receipts.
- `runs/`, `sta/`, `upstream/data/`, `numerical_evidence/`: populated by release packages and ignored by Git.

Original code and owned computed outputs: MIT. Third-party inputs and derived design artifacts retain their own terms. Use the repository URL as the code/data availability link; use tag `v1.0.0` for the reproducible snapshot.
