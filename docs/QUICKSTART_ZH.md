# Quickstart

This repository provides code, datasets, models, and results for **Support-Conditioned Residual Gating for Sparse Capacitance Completion**. See the [README](../README.md) for the main results and figure/table links. Large datasets and models are distributed through GitHub Releases.

## Installation and inference

Run the following commands with Python 3.10 or newer:

```bash
git clone https://github.com/GRYYYYYYY/residual-gating-capacitance.git
cd residual-gating-capacitance
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m capdata fetch database models
python -m capdata list
python scripts/inference_demo.py --domain reference
```

For data-only use, the download command requires only the Python standard library; PyTorch is not required. Install the research dependencies for model inference and training.

```python
from capdata import load_tables

train = load_tables("public_rules_holdout")
reference_train = load_tables("reference_original")
confirmation = load_tables(
    "eval_reference_confirmation_round3_main", partition="confirmation"
)
```

Public rule tables and generated FEM tables differ in physical meaning, units, and output channels. Use them as separate datasets. The loader defaults to the training partition; keep validation, confirmation, test, and STA evaluation records separate from training.

## Dataset management

- `database/catalog.json`: dataset IDs, roles, versions, sizes, units, splits, packages, and relative paths.
- `database/packages.json`: archive names, sizes, and SHA-256 checksums.
- `database/files.json` and `database/files-extended.json.gz`: exported-file and source-file hashes.
- `configs/selected_models.json`: the selected checkpoints for all four domains.

To download and verify every package:

```bash
python -m capdata fetch --all
python -m capdata verify --all
```

To install artifacts in a separate directory, pass `--root /path/to/data` and set `RG_DATA_ROOT` before loading them. Run experiment drivers that use repository-relative `runs/` paths from the repository root.

To install previously downloaded archives:

```bash
python -m capdata fetch database models --from-dir /path/to/downloads
```

These commands can be repeated safely. The installer refuses to overwrite local files whose contents differ from the released hashes.

## Reproduce tables and figures

```bash
python -m capdata fetch database experiment-records sta-visualization
python scripts/reproduce_reports.py --sta --output results/my_reproduction
```

This command checks all 39 result tables byte-for-byte against the released versions and rebuilds STA spatial figures from recorded endpoints, paths, and coordinates. It reuses recorded measurements. For full scoring, retraining, and saved-layout STA replay, see the [reproduction guide](REPRODUCING.md).

## Models and numerical evidence

`configs/selected_models.json` identifies the three selected model members for each of the four domains, together with their checksums. Other checkpoints support initialization, model selection, or ablation studies.

The optional numerical-evidence package contains FEM configurations, results, logs, and solver source code. Original CTF inputs are retrieved separately using the pinned download script. Third-party rule and layout licenses are documented in [THIRD_PARTY.md](../THIRD_PARTY.md).
