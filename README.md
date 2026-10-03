# Chip Capacitance Prediction by a Jointly Routed Transformer

Code, datasets, trained models, and results for the paper **Chip Capacitance Prediction by a Jointly Routed Transformer**.

[Quickstart](docs/QUICKSTART_ZH.md) · [Reproduction guide](docs/REPRODUCING.md) · [Dataset catalog](docs/DATABASES_ZH.md) · [Downloads](https://github.com/GRYYYYYYY/residual-gating-capacitance/releases/tag/v1.1.0)

## Method

The model predicts missing capacitances from candidate geometries, structural/material context, and the observations available in each table. A shared Transformer drives a neural residual and a component-wise gate. The gate combines numerical and neural corrections around a support-derived interpolation anchor. Masked completion jointly trains both heads; inference retains observed entries exactly.

The same formulation supports interpolation, extrapolation, and source-only transfer. Transfer uses the target table's available observations without updating model parameters. The support anchor is evaluated separately from the commercial-style multilinear baseline because they can differ on multidimensional tables.

## Final-paper scope and results

The authoritative manuscript is [the final paper](paper/paper.pdf), titled **Chip Capacitance Prediction by a Jointly Routed Transformer**. Its [LaTeX source](paper/main.tex), [tables](paper/tables), figures, and [SHA-256 manifest](paper/manifest.json) are included. The paper studies prediction from sparse observations, not reconstruction of an assumed complete physical table. Extrapolation is relative to the currently observed geometry support; it does not necessarily mean extrapolation outside the training distribution.

| Evaluation | Final-paper result | Evidence |
|---|---|---|
| Main prediction comparison | Lower NRMSE than rank-matched commercial-style multilinear interpolation in **15/15** settings; better than the strongest listed numerical/statistical comparator in **14/15** | [Table 1](paper/tables/main_completion.tex), [Table 2](paper/tables/main_transfer.tex) |
| Public-rule extrapolation | **84–86%** lower normalized error outside observed support at 30% missingness | [Table 1](paper/tables/main_completion.tex) |
| Source-only transfer | **FreePDK15 → ASAP7**, eight target confirmation tables; target observations are inference inputs, with no parameter updates or target-label model selection | [Table 2](paper/tables/main_transfer.tex) |
| Fixed-layout extraction and timing | Closer capacitance and worst-slack estimates in **16/16** settings across eight routed layouts | [Table 3](paper/tables/main_downstream_compact.tex), [Figure 3](paper/sta_visualization/gf180_ibex_50/figures/fig_downstream_sta_spatial_row.pdf) |
| Matched-budget learned controls | Full routing beats ungated residual in **14/15**, binary gate in **13/15**; gains depend on the setting | [Learned controls](paper/tables/supp_matched_controls.tex), [paired intervals](paper/tables/supp_control_bootstrap.tex) |
| Numerical extrapolation control | Full model beats validation-selected local affine extrapolation in **13/15** settings | [Affine control](paper/tables/supp_affine_control.tex) |

Public labels are extraction-rule values. Independent reference labels come from declared two-dimensional finite-element problems. Downstream results measure agreement with full-table extraction on fixed layouts, not timing closure or silicon accuracy. Full routing is not uniformly best: the binary gate wins two transfer conditions, the ungated model wins public in-support block masking, and local affine wins FEM/transfer out-of-support random masking. See [final-paper alignment and split definitions](docs/FINAL_PAPER.md).

## Data and models

- **Public rules:** 1,713 capacitance tables from ASAP7, GF180, IHP-SG13G2, and Sky130. The public model excludes all 84 downstream audit tables from its training, validation, and test inventory.
- **Independent FEM reference:** 16 original fitting tables (153 nodes each), a separate 24-table validation cohort, and 16 confirmation tables from the 27-table, 8 × 16 Round-3 collection. The collection also contains eight validation and three boundary tables; these are distinct from the fitting inventory and the 24-table selection cohort.
- **Final-paper transfer:** eight FreePDK15 fitting tables, 12 FreePDK15 validation tables, and eight ASAP7 confirmation tables.
- **Downstream evaluation:** eight fixed routed layouts and 104 reference/baseline/model SPEFs.

[Final-paper models](configs/paper_models.json) identifies the three checkpoints for each of the three final-paper settings and their hashes. [The dataset catalog](database/catalog.json) defines units, splits, and the training and evaluation datasets. Derived views are not additional independent physical samples.

Large artifacts are [v1.1.0 Release downloads](https://github.com/GRYYYYYYY/residual-gating-capacitance/releases/tag/v1.1.0). Superseded result tables and the old v1.0.0 Release have been removed. The core packages are `database`, `models`, and `experiment-records`; add `sta-visualization` for spatial figures and `sta-layouts` for saved-layout timing replay. Optional numerical evidence and saved-layout inputs are listed in the [package manifest](database/packages.json).

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

Use `--domain public` or `to_asap7` for the other final-paper settings. Each demo evaluates one held-out episode; full scoring and retraining commands are in the [reproduction guide](docs/REPRODUCING.md). Data download and verification use only the Python standard library.

```python
from capdata import load_tables

train = load_tables("public_rules_holdout")
confirmation = load_tables(
    "eval_reference_confirmation_round3_main", partition="confirmation"
)
```

The loader defaults to the training partition. Set `RG_DATA_ROOT` to use a separate artifact directory.

## Verify final-paper evidence

```bash
python scripts/verify_final_paper.py
```

This checks the manuscript manifest, final-paper scope, headline counts and supplementary score aggregates. [Supplementary control reproduction](experiments/paper_controls/README.md) provides fresh training/scoring and recorded-result regeneration.

## Export final-paper tables and redraw Figure 3

```bash
python -m capdata fetch database experiment-records sta-visualization
python scripts/reproduce_reports.py --sta --output results/my_reproduction
```

This verifies the final-paper evidence, exports only the tables used by the final manuscript, and optionally redraws the horizontal Figure 3. Table export preserves manuscript formatting; it is not a fresh training or STA run.

Validation records cover final-paper table aggregation, matched controls, figure regeneration, and saved-layout STA replay. Run lightweight checks with:

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
