# Matched OpenRCX-kernel downstream comparison

This bounded addition evaluates the same OpenRCX kernel as Fig. 4 on the fixed
B=4/8 rule-completion support used by the MLI-ext./Full downstream study.
It adds 48 native extraction/STA runs: eight unchanged layouts, two budgets,
and seeds 11/29/47. MLI-ext., Full, and golden results are reused unchanged.

## Algorithm and protocol

- Read the exact 498 support episodes from
  `results/dac_characterization_20261114/downstream/rules/manifest.json`.
  The same 83 eligible tables, observed entries, completed rows, and targets are
  used. No training, support selection, layout perturbation, or model search.
- Evaluate `experiments/pex_kernel_revision/kernels.py:openrcx` at the represented
  geometry of each nonobserved rule node, with the same coordinate scales as
  `coverage.py`: GF180 2000 units/um, other processes 1000 units/um.
- Check every exported query against the C++ harness containing the extracted
  pinned OpenRCX function bodies (source commit
  `0b54bb3203e0895f87940ff982358a6e4d406e28`). This covers width mapping,
  four-unit distance slots, and first/last measurement returns.
- Use the same scalar component wrapper as Fig. 4, including DIAGUNDER table
  components. This is the stated kernel control; it is not a test of the native
  diagonal-specific API. Finite represented coordinates are used throughout.
- Write only the common nonobserved coupling/ground fields. Observations,
  resistance, unselected tables, context, and all other rule fields are retained.
  The existing exporter checks round-trip values and byte-exact unmasked lines.
- Run the unchanged extraction/STA Tcl on the original ODB, SDC, libraries,
  executable, and golden reference. This is fixed-node rule completion followed
  by native extraction, not computeTable population or online replacement.

## Execute

From the repository root with the original local native dependencies available:

```bash
source experiments/dac_characterization_20261114/env.sh
"$DAC_PYTHON" experiments/downstream_kernel_comparison_20261117/run.py --export
"$DAC_PYTHON" experiments/downstream_kernel_comparison_20261117/run.py --pilot --workers 1
"$DAC_PYTHON" experiments/downstream_kernel_comparison_20261117/run.py --run --workers 4
```

Export refuses to replace existing rules. Native runs use exclusive output
directories and skip only completed runs with matching rule hashes. Golden
directories are read-only links to the completed reference runs. Outputs reside
under `results/downstream_kernel_comparison_20261117`. Each OpenROAD process
uses one thread with a 300-second timeout; concurrency is capped at four.

## Rebuild paper artifacts

```bash
source experiments/dac_characterization_20261114/env.sh
# First collection only; this refuses to overwrite an existing raw bundle.
"$DAC_PYTHON" paper/dac_layout_query_revision/build_downstream_two_kernels.py --collect
# Subsequent rebuilds use the checked portable bundles, with no native tool run.
"$DAC_PYTHON" paper/dac_layout_query_revision/build_downstream_two_kernels.py
cd paper/dac_layout_query_revision
TEXINPUTS=.:..: pdflatex -interaction=nonstopmode -halt-on-error main.tex
TEXINPUTS=.:..: pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The new raw bundle is under `paper/dac_layout_query_revision/data/downstream_two_kernels`.
The existing `data/downstream_matched_mli/raw_inputs.json.gz` supplies the reused
MLI/Full and golden evidence. Both bundles have SHA256 manifests. The builder
checks the identical support manifest, rule hashes, ODB/SDC/library/executable/Tcl
provenance, unchanged resistance, identical net and endpoint sets, and placement.

Table III reports `100*(1-mean(Full error)/mean(baseline error))` for B=4/8.
Errors are net-C NRMSE and absolute WS/TNS deviations against full-rule extraction,
averaged across seeds before computing the reduction. Negative reductions are
retained. Dashes denote zero error for both methods, not missing runs.

Fig. 5 uses B=8 and all three seeds. Columns are four processes; the top and bottom rows show
MLI-ext.-minus-Full and OpenRCX-kernel-minus-Full absolute slack errors, respectively. Endpoint
errors are computed per seed before averaging, then averaged in 50x50 spatial
bins. Each column shares one symmetric color scale across both baselines. Gray
marks empty bins, blue improvement, red degradation; MAE annotations are in ps.
