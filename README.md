# Support-Conditioned Residual Gating for Sparse Capacitance Completion

Code, datasets, trained models, and results for the paper **Support-Conditioned Residual Gating for Sparse Capacitance Completion**.

[Quickstart（中文）](docs/QUICKSTART_ZH.md) · [Reproduction guide](docs/REPRODUCING.md) · [Dataset catalog](docs/DATABASES_ZH.md) · [Downloads](https://github.com/GRYYYYYYY/residual-gating-capacitance/releases/tag/v1.0.0)

## Method

The model predicts missing capacitances from candidate geometries, structural/material context, and the observations available in each table. A shared Transformer drives a neural residual and a component-wise gate. The gate combines numerical and neural corrections around a support-derived interpolation anchor. Masked completion jointly trains both heads; inference retains observed entries exactly.

The same formulation supports interpolation, extrapolation, and source-only transfer. Transfer uses the target table's available observations without updating model parameters. The support anchor is evaluated separately from the commercial-style multilinear baseline because they can differ on multidimensional tables.

## Results

| Evaluation | Main finding | Results |
|---|---|---|
| Table completion | Lower NRMSE than the applicable commercial-style multilinear rule in 19/20 headline settings and the strongest applicable baseline in 16/20 | [Public: in-table](results/expected_tables/public_confirmation_inside.tex), [out-of-table](results/expected_tables/public_confirmation_outside.tex); [FEM reference](results/expected_tables/reference_confirmation.tex) |
| Public-rule extrapolation | 84–86% lower out-of-table NRMSE at 30% missingness | [Public out-of-table results](results/expected_tables/public_confirmation_outside.tex) |
| Source-only transfer | Evaluated in both directions between ASAP7 and FreePDK15, with in-table and out-of-table results separated | [Transfer results](results/expected_tables/transfer_merged.tex) |
| Fixed-layout extraction and timing | Closer capacitance and worst-slack estimates in all 16 design–process–mask settings across eight routed layouts | [Downstream summary](results/expected_tables/downstream_summary.tex), [full results](results/expected_tables/downstream_detail.tex) |
| Ablations and efficiency | Correction branches, routing, training choices, and measured runtime | [Ablations](results/expected_tables/ablations.tex), [branch study](results/expected_tables/elements.tex), [runtime](results/expected_tables/runtime_summary.tex) |

Public labels are extraction-rule values. The independent reference uses declared two-dimensional finite-element problems. Downstream results measure agreement with full-table extraction on fixed layouts, not timing closure or silicon accuracy. Detailed endpoint results retain all three seeds, including the seed with slightly higher MAE despite lower RMSE.

## Data and models

- **Public rules:** 1,713 capacitance tables from ASAP7, GF180, IHP-SG13G2, and Sky130. The public model excludes all 84 downstream audit tables from its training, validation, and test inventory.
- **Independent FEM reference:** 27 tables on an 8 × 16 geometry grid: 16 confirmation tables, eight validation tables, and three boundary tables.
- **Transfer:** eight confirmation tables for each target, ASAP7 and FreePDK15.
- **Downstream evaluation:** eight fixed routed layouts and 104 reference/baseline/model SPEFs.

[Selected models](configs/selected_models.json) identifies the three checkpoints per domain and their hashes. [The dataset catalog](database/catalog.json) defines units, splits, and the training and evaluation datasets. Derived views are not additional independent physical samples.

Large artifacts are GitHub Release downloads. The core packages are `database`, `models`, and `experiment-records`; add `sta-visualization` for spatial figures and `sta-layouts` for saved-layout timing replay. Optional numerical and supplementary records are listed in the [package manifest](database/packages.json).

## Quickstart

Python 3.10 or newer:

```bash
git clone https://github.com/GRYYYYYYY/residual-gating-capacitance.git
cd residual-gating-capacitance
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

python -m capdata fetch database models
python -m capdata verify --package database
python scripts/inference_demo.py --domain reference
```

Use `--domain public`, `to_asap7`, or `to_freepdk15` for the other domains. Each demo evaluates one held-out episode; full scoring and retraining commands are in the [reproduction guide](docs/REPRODUCING.md). Data download and verification use only the Python standard library.

```python
from capdata import load_tables

train = load_tables("public_rules_holdout")
confirmation = load_tables(
    "eval_reference_confirmation_round3_main", partition="confirmation"
)
```

The loader defaults to the training partition. Set `RG_DATA_ROOT` to use a separate artifact directory.

## Reproduce paper tables and figures

```bash
python -m capdata fetch database experiment-records sta-visualization
python scripts/reproduce_reports.py --sta --output results/my_reproduction
```

This regenerates and checks all **39 result tables** against the released results and rebuilds the STA figures from recorded measurements. It does not retrain models or rerun field solvers. Fresh inference, full scoring, retraining, and saved-layout STA replay are documented separately in the [reproduction guide](docs/REPRODUCING.md).

Validation records in `results/` cover four-domain inference parity, table reproduction, package integrity, and saved-layout STA replay. Run lightweight checks with:

```bash
python -m unittest discover -s tests -v
```

## Repository structure

| Directory | Purpose |
|---|---|
| `unified/` | Tokenization, residual gating, correction operators, training, and scoring |
| `pdkcap/`, `openrcbench/`, `solver/` | Data preparation, rule parsing/export, and FEM implementation |
| `capdata/`, `database/` | Dataset loader, download interface, catalogs, and checksums |
| `scripts/`, `analysis/` | Inference, reproduction, and figure/table generation |
| `results/` | Result tables, figures, and verification records |

## License

Original code and owned computed outputs are released under [MIT](LICENSE). Third-party rules, PDKs, and design artifacts retain their [upstream licenses](THIRD_PARTY.md). Original CTF inputs are retrieved separately using the pinned download script described in the reproduction guide. Archive and member checksums are provided with every download.
