# Runtime and accuracy continuation

The authoritative paper remains `paper/dac_layout_query_revision/main.tex`.
This continuation starts at `175fe3877e3f20de87f8fcb701b8df115802edd6` and does not
change the frozen model, native layout, support, reference or source-training
artifacts. The reference identities and physical limitations in
`docs/layout_offgrid_20261115/REPRODUCE.md` continue to apply.

## Run

From the repository root:

```bash
bash experiments/runtime_accuracy_20261115/run.sh --analysis
# Recompute timings sequentially on the provisioned environment:
bash experiments/runtime_accuracy_20261115/run.sh --full
latexmk -pdf -interaction=nonstopmode -halt-on-error -cd paper/dac_layout_query_revision/main.tex
python3 paper/dac_layout_query_revision/sync_markdown.py
```

`--analysis` needs the committed small result files (compressed CSV/JSONL files
are unpacked by the entry point), regenerates measured tables/figures and the
runtime subsection, compiles both PDFs, and synchronizes the reading copy.
`--full` additionally needs the existing
immutable local checkpoints, CTF-derived support data, OpenROAD/PDK/STA inputs,
and native traces identified in the preceding layout-query release. It does not
download or redistribute those inputs. The native C++ harness can be reproduced
from its committed compact input without the large traces.

The entry point sources the existing Python environment; the single-RHS FEM
worker uses the existing gmsh/skfem environment and its libGLU path. It pins work
to logical CPU 24 (NUMA node 0), with OMP/MKL/OpenBLAS/PyTorch threads set to one.
`RUNTIME_CPU` may select another permitted CPU; record that change. The machine
is shared, without an exclusive reservation, fixed frequency, or flushed file
cache. Do not run phases concurrently. No GPU environment is installed or
estimated. `environment.json` records actual hardware and library versions.

## Workload and timing boundaries

- FEM: exactly the 71 formal query IDs and six original 153-sample support sets.
  Ground and summed lateral coupling are the nonzero outputs in F/m. Diagonal
  output is retained, without counting it as another geometry query.
- Native: exactly 480 frozen unique geometries and 42 held-out source-rule
  groups, with all supplied samples. The reference is OpenRCX's return value,
  not independent electrostatic truth. Native physical alignment remains absent.
- Canonical evaluation is all S plus hash-sorted Q chunks of at most 32, with
  the same three members. Equivalence to the frozen outputs is checked before
  timing. Q limits 1, 8, and 32 each have their own predictions and errors.
  A block covers each requested geometry once; its denominator is 71 or 480,
  never 32 or the number of support/material tokens.
- Three warmups and 20 timed blocks use seed 20261115 to interleave methods and
  contexts. Query-table construction, all numerical candidates, feature packing,
  all three forwards and output assembly are included. Mean/median/P95 batch
  latency and total-time/query-count are distinct. Only Q=1 yields a measured
  single-request latency distribution. CPU and wall clocks are both retained.
- MLP adapts each of its three frozen members once per support/context using the
  source-selected update count. The fit uses support labels only. Its warm query
  path evaluates Q alone; numerical equivalence to the original S+Q fit/forward
  is verified. The first fit includes first-use optimizer initialization, which
  is not silently removed from the one-time cost. The same policy applies to the
  existing component-supervised AttentionCap adapter (source-selected 50 steps).
- No Transformer support hidden state is cached, because the global union
  attention and support envelopes depend on Q. The other research numerical
  methods retain their original setup inside each call. No exact answer cache
  or native-distance quantization is used as a neural cache key.
  Fixed-S factor caches could further accelerate the research numerical/CNP
  implementations; these measurements do not bound an optimized implementation.
  A support, process or corner change invalidates retained fits and exported rules.
- `forward_s` for Full/Binary/Residual includes the three forwards and immediate
  rescaling; ensemble reduction is in `postprocess_s`. `numerical_s` includes
  support geometry/envelopes and the candidate bank. CNP was separately remeasured
  to expose its three original encodings/forwards rather than label its complete
  prediction call as forward-only; predictions are bit-identical. Superseded
  combined timings are retained for audit, not selected by speed.
- Process RSS is a peak/shared-process measure, not isolated model memory.
  `cold_load.json` reports fresh-process startup, imports, weights and peak RSS;
  file-system caches are uncontrolled. The existing control loader loads a
  Full/Binary/Residual bundle and is explicitly identified as such. Its time is
  not falsely assigned to a single Binary model. Preparation JSON keeps shared
  bundle loading separate from per-context fitting.

## Matched field solving

The resident solver regenerates each original fine mesh, assembles its P2
stiffness, factors it once, drives only the target conductor, and projects the
reaction charges into the same three components. Maxwell reciprocity permits
using the target column instead of the target row; every query is checked
against the independently certified full matrix. There is no reuse of query
answers, meshes, matrices or factors across geometries/repeats. Within a query,
one factor and one RHS serve both nonzero outputs.

Three complete resident passes are randomized after one warmup. Initialization,
meshing, assembly, factorization, RHS solve and projection are separately timed.
The full-matrix coarse/fine/wide certification remains the uncertainty evidence;
it is not charged as a normal production solve. `solver_task_match.json` also
joins the recorded cold fine-only and three-level certification receipts to the
same 71 IDs. Sum of worker times is used, not parallel cohort elapsed time.
Inference errors substantially exceed reference uncertainty; a runtime ratio
alone does not establish equal accuracy to a direct fine solve.

## Native computation and extraction

`native_lookup.cpp` is a source-validated C++ counterpart of finite, non-sentinel
`getComputeRC` behavior after width/context resolution, including the distance
compute grid. It is **not** the linked OpenRCX binary or the full geometry
discovery/width-selection path. All 480 values are checked against recorded
OpenRCX outputs before accepting its timings. An initial pilot freezes a loop
length targeting 30 ms; three warmups and 20 loops retain a checksum. The timed
region has no trace, SPEF, Python or Tcl IO. A separate ctypes loop measures
cross-boundary calling plus checksum overhead; neither loop provides an actual
single-request P95. The compact input and compiler flags/hashes are retained.
This cycles a cache-hot corpus; it does not reproduce arbitrary PEX access
locality. To rebuild the harness alone:

```bash
g++ -O3 -DNDEBUG -std=c++17 experiments/runtime_accuracy_20261115/native_lookup.cpp -o /tmp/dac-native-lookup
/tmp/dac-native-lookup results/runtime_accuracy_20261115/native_kernel_input.txt
```

Native flow uses the unchanged release OpenROAD executable, eight fixed ODBs,
and original/CMI/Binary/Full rules at B=8, seed 11. The 83 eligible source-held-out
tables use the original support and candidate-node protocol; exported files
must be byte-identical to the previously verified exports. This is same-node
completion, not additional-node enrichment and not the all-support FEM cohort.
Preparation measures input loading, shared support selection/model loading,
prediction and export separately. Full/Binary have no target adaptation.

Three randomized complete passes (96 fresh processes) separate layout/library
loading, rule registration, `extract_parasitics`, SPEF writing, SPEF reading and
STA analysis. Rule registration only assigns the filename in this OpenROAD
revision (`extRCap.h`); parsing remains in extraction. RSS before/after registration
and extraction and total peak RSS are measured, but neither isolated rule-parse
time nor rule-only allocated memory is claimed. C/STA fidelity is checked against
the same immutable native reference. Native counts are not used as timing fractions.

The measured reuse case is two designs per process, eight designs across four
rule libraries. Preparation prediction spans all four processes and is counted
once per method; export is per library. Source training and original support
characterization are shared frozen inputs, with their provenance and receipts
retained in the earlier experiment directories. No source training is repeated.
No arbitrary large reuse count is assumed to hide preparation costs.

The accounting model is
`T_target = T_load + T_support_prepare + T_target_adapt + sum(T_query_batches) + T_export`.
For offline reuse,
`T_total(D) = T_rule_prepare + sum_d(T_native_extract_d + T_output_d)`.
The measured example uses D=8 (two designs for each of four distinct process
libraries). Shared preparation is charged once in the comparison study, not
once for every query or method. `deployment_cost.json` reports marginal costs
after this shared setup and lists the shared setup separately. STA is additional.
No off-grid occurrence fraction is substituted for a measured time fraction.

## Scope and retained failures

This delivers query-level replay, matched template-reference timing and native
timing after fixed-node offline export. Dense-node enrichment and online model
replacement remain unimplemented. AttentionCap is the existing adapted 2D
component-supervised version, not its original matrix-supervised benchmark.
Its full CTF feature stack plus an explicit extent and ground token is checked
against the solver's merged dielectric layers and air above the stack. Two
initial checks incorrectly assumed identical material-list serialization;
their logs are retained. The corrected check compares the physical permittivity
function, conductor rectangles, ground boundary and projection, without changing
the model or any labels. Flash-CNNCap's 3D windows do not share this task, so no
cross-paper speed ratio is made. No parameters were searched using query accuracy.

A duplicate metadata key interrupted the first solver launch before any solve;
the corrected join keeps the original receipt fields. OpenSTA prints the `max`
qualifier in worst-slack/TNS lines; the initial summary parser missed it. The
retained logs were reparsed, with explicit ns/ps conversion, without rerunning
or altering any extraction timing. Small implementation fixes and superseded
measurements remain in the review artifacts.

Large generated SPEFs, rule files and compiled binaries remain local and are
hash-indexed. Small raw timing/prediction records, summaries, figure code, TeX,
PDF and this procedure are the reviewable deliverables.
