# Layout-query experiment and paper reproduction

Run from the research worktree:

```bash
bash experiments/layout_offgrid_20261115/reproduce.sh --analysis
```

This verifies the recorded results, rebuilds figures and both PDFs, and generates
the reading copy. `--full` also runs/resumes native extraction, direct references,
and fixed-model predictions. It never routes layouts or trains new source models.
Reference reuse verifies each spec; native receipts preserve layout/rule/binary
hashes. Keep the released frozen query plans: they define sampling, pilot/formal
separation, inclusion probabilities and the protocol, not runtime suggestions.
The one extra initial control is retained separately. The scalar fit loops are
existing 200-step source-selected MLP adaptations using S alone.

The setup uses the existing local paths in
`experiments/dac_characterization_20261114/paths.json`, original ODB/SDC/library
inventory `database/sta_cases.json`, model manifest `configs/paper_models.json`,
and installed Python/tool environments. On another machine, install those input
artifacts according to the repository catalog and adjust the explicit installation
paths in `build_trace.py`, `run_native.py`, `reference.py`, and `contracts.py`.
This is an executable local reproduction, not a container claiming independence
from licensed/download-only input availability. No vendor CTF or trained weights
are redistributed in the review ZIP. Input paths and hashes identify them.

## What each result means

- `query_manifest.jsonl`, `query_census.csv`: 9,888,586 calls to two native
  capacitance getters across eight unchanged layouts; 19,562 unique keys.
  Raw coordinates mean **arguments arriving at these getters**, not a complete
  unquantized conductor slice. Integer native scale/DBU fields are explicit.
  This is a partial getter census, not the total number of every PEX operation.
- `native/*/*/trace.tsv`: raw calls and original measurement knots before the
  internal computation grid is generated. Original/trace SPEF electrical text
  is identical in every case. Raw traces, executables and SPEFs stay local.
- `native_validation.json`: independent finite-range reimplementation validated
  against actual OpenRCX; it is not renamed as an original native binary.
- `predictions_native.jsonl`: nine predictors, 480 off-grid geometries, 42
  source-held-out rule groups, all original support labels. Reference values
  are native outputs. Errors measure **native agreement**, not physical accuracy.
- `reference_plan.json`: six ASAP7 M4/M5 contexts and 114 eligible geometries
  accounting for 86,587 calls. Geometry-only stratification fixes 12 pilot and
  71 formal geometries. Coordinates are genuinely absent from the original
  CTF grid at native DBU resolution. These are existing AES/Ibex layouts, not
  unseen-design tests. `template_coverage.json` includes the natural denominator.
- `reference_results/*/{coarse,fine,wide}`: 288 direct solves including 12
  controls and an initial extra control. Each contains input, full Maxwell,
  reaction/energy/flux matrices, solver diagnostics, CPU/wall receipts and logs.
  Mesh files remain local. Hash-verified reused support uses the same frozen
  solver source and exact specifications, with all 153 samples per context.
- `predictions_fem.jsonl`: nine methods on all 71 converged formal geometries.
  Its physics is **LAYOUT_PARAMETERIZED_TEMPLATE**, not an exact layout section
  or a verified native simplified pattern. Mirror side wires, finite adjacent
  context planes, exterior ground, isotropic horizontal materials and infinite
  extrusion are explicit. F/m labels sum lateral coupling and separately count
  ground/context contributions. No arbitrary length multiplication is applied.
- `paired_metrics.csv`: same-Q comparisons by family/component, process/design,
  unique weight and occurrence/inclusion-probability weight. NRMSE is undefined
  for zero-truth components, which retain MAE/P95/P99/signed error. Rows are
  paired descriptive results; no independence-based significance claim.
- `costs.csv`: batch costs counted once, not once per replicated query row.
  MLP cost includes adaptation; full/binary cost includes encoding and forwards.
  Separate encoding/fit/forward splits were not instrumented in these timings.
  Model loading is excluded; reference evaluation labels are not deployment cost.

## Physical and deployment limits

`physical_contracts.json` and `NATIVE_CALLMAP.md` record why the native rules
cannot currently be scored against the CTF FEM as the same physical system.
Exact-layout-section count and physically aligned native/FEM count are zero.
This gap is not silently calibrated away. Native replay is complete; template
reference evaluation is complete; new rule-node enrichment and in-extractor
replacement are not implemented. Existing fixed-grid export/PEX/STA evidence
remains in the paper as full-rule fidelity, not independent physical truth.

Full does not beat interpolation here: template unique-geometry macro NRMSE is
Anchor 0.004512, Full 0.016755, Binary 0.022181 and adapted MLP 0.018890. Native
agreement is also substantially better for Anchor than learned correction.
These negative findings are in the abstract, results and conclusion.

## API and batch boundary

`unified/queries.py::predict_queries` accepts only S values and Q coordinates.
It preserves `predict_table` exactly with the original candidate order and
restores only exact-coordinate support. The main policy canonicalizes Q by
geometry hash, retains all S and uses chunks of at most 32. No Q labels, Q
normalization fit, nearest-node pseudo-labels or source retraining are used.

`api_checks.json` distinguishes canonical input reordering, raw token ordering,
set-size changes and adding unlabeled queries. Raw FEM reordering changes Full
by up to 0.003194 source-scaled units; `raw_order_diagnosis.json` finds changed
support envelopes/gate descriptors despite identical features and anchor.
Consequently raw-order equivariance is NOT claimed. Canonical protocol replay
is invariant to user input reordering, but predictions remain batch-conditioned.
The source numerical semantics were not changed to conceal this behavior.

## Resource and artifact policy

Config: 64 core-hour maximum, 8 core-hours integration allowance, at most four
single-thread solver workers, no GPU or new source training. Measured main stages
sum to about 0.72 core-hours. A conservative eight core-hour all-inclusive charge
covers checks, bookkeeping, failed preflights and the discarded partial scorer;
it is an upper bound, not an invented precise CPU measurement. Partial scorer
outputs were saved under `partial_unscored_*` and are excluded from final tables.
All 71 formal geometries were subsequently scored together after solver completion.

Authoritative manuscript: `paper/dac_layout_query_revision/main.tex`.
The editable expanded treatment `extended.tex` preserves the full support
analysis and detailed earlier results; `main.tex` follows the DAC content limit.
The supplied task materials and hashes are retained in `task_inputs/`.
