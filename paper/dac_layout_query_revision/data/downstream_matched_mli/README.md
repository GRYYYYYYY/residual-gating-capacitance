# Matched MLI downstream evidence

Table III and Fig. 5 use the completed fixed-budget native runs in
`results/dac_characterization_20261114/downstream`, not the separate 30%/50%
block-holdout runs whose recorded `linear` method mixes linear interpolation
and two-neighbor IDW. Those earlier inputs and figures remain preserved under
`data/downstream_fidelity` and `figures/downstream_spatial_*`.

The baseline here is **MLI-ext.**, the operator implemented by
`experiments/pex_kernel_revision/kernels.py:mli(extension=True)` and named in
the paper's baseline definitions. The raw run identifier is `cmi`. This mapping
is established by evaluating that actual MLI implementation on every archived
support set and comparing every exported prediction component with the archived
CMI payload. The 498 support episodes are all rank one; complete-cell evaluation
and boundary clamping occur, with no missing-corner completion required in this
cohort. The largest absolute difference is 2.710505431213761e-20 across 6,108
prediction components. This equality is established on this cohort, not asserted
for arbitrary higher-dimensional inputs or commercial software.

## Protocol and aggregation

- Eight layouts: AES and IBEX on ASAP7, GF180, IHP-SG13G2, and Sky130HS.
- Budgets B=4/8, capped by available candidate count; common farthest-point support
  and seeds 11/29/47. The export manifest supplies all support indices.
- 83 eligible held-out tables are completed. Other tables, observed rows, and
  resistance are retained. This is fixed-node rule export, not computeTable injection.
- Table III: 96 completed method/layout/budget/seed runs plus eight golden runs.
  Each metric is averaged over the three seeds before computing
  `100 * (1 - Full_error / MLI_error)`. WS and TNS are absolute deviations from
  full-rule extraction, expressed in ns in the CSV. A dash denotes a zero/zero
  TNS comparison, not a missing evaluation. This seed-mean convention replaces
  the maximum-over-seeds convention in the separate block-holdout table.
- Fig. 5: B=8, four IBEX layouts, all three seeds. Compute endpoint absolute slack
  errors against the same golden extraction, average errors over seeds, then
  average MLI-minus-Full differences within each 50x50 spatial bin. Values and
  annotations are in ps. Panels use individual symmetric color scales.

## Reproduce

From the repository root:

```bash
source experiments/dac_characterization_20261114/env.sh
"$DAC_PYTHON" paper/dac_layout_query_revision/build_downstream_matched_mli.py
cd paper/dac_layout_query_revision
TEXINPUTS=.:..: pdflatex -interaction=nonstopmode -halt-on-error main.tex
TEXINPUTS=.:..: pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

`raw_inputs.json.gz` contains the native completion/provenance records, golden
unit logs, B=8 IBEX endpoints and placement, exact support manifest, source tables,
CMI prediction payloads, and original summary CSV. `sources.json` verifies each
input's SHA256. `--collect` is only for initial collection and refuses to overwrite
an existing bundle. Normal reproduction needs no external STA installation or
model checkpoints and performs no training or extraction.

The script checks common ODB/SDC/libraries/executable/Tcl hashes, rule hashes
against the export manifest, unchanged resistance, identical net/endpoint sets
and placement, native slack consistency, and the original unrounded summary.
The accumulated endpoint TNS check uses the archived audit tolerance of 0.02
native time units; displayed WS/TNS values come from native aggregate records.

Generated artifacts are `tables/downstream_matched_mli.tex`,
`figures/downstream_matched_mli.pdf` and `.png`, and this directory's
`native_metrics.csv`, `reductions.csv`, `spatial_seeds.csv`,
`*_endpoint_seedmean.csv.gz`, and `verification.json`.

The reused preparation timings remain measurements of the archived CMI implementation, whose outputs match MLI-ext. on this cohort; the verification does not claim equal execution time between independent implementations.
