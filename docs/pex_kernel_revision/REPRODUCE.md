# PEX kernel and compute-table continuation

The revision continues research branch `research/dac-capacitance-characterization-20261114` from verified `a519539fee8a763c74e1db61427fdd02d85511ca`. Main and original inputs remain untouched. The supplied task and supplementary texts are retained in `task/`. No source model training or field solving is repeated.

## Entry points

```bash
# Rebuild result tables, figures, manuscripts and receipts from recorded outputs:
bash experiments/pex_kernel_revision/run.sh --analysis
# Rebuild isolated OpenROAD variants and rerun the bounded pipeline:
bash experiments/pex_kernel_revision/run.sh --full
```

Full replay requires the existing local immutable checkpoints, routed databases, process rules, libraries and source/build tree specified by the preceding releases. They are not redistributed. The extracted finite kernel can be rebuilt from committed `pinned_kernel.cpp` using `g++ -O3 -DNDEBUG -std=c++17`; it uses the pinned Array1D storage header and a finite, non-sentinel CLI wrapper. The full hook is shipped as readable source plus a pinned-source patch. It patches a copied translation unit and archive; it does not mutate the installed OpenROAD or its source.

The analysis entry requires the repository's existing Python environment (NumPy/SciPy/Matplotlib), TeX installation and prior small result files. Timing/accuracy CSV and gzipped raw accumulators are committed. Large SPEFs, binaries, archives, pointer-rich getter logs and model weights stay local. Receipts, hashes, compact injection payloads, comparisons and validation counts accompany them.

## Workload contracts

`baseline_contracts.json` is the naming and scope contract. The user supplied the xRC mathematical core, not a commercial binary or complete boundary policy. Accordingly the public baseline is **specified MLI**. Complete-cell MLI is independent code tested at ranks1/2/4, including mixed terms. Sparse support uses the previously specified support-only CMI completion as an explicit extension; clamping and off-affine-coordinate projection are separately marked. The current physical datasets have ranks1/2. Rank4 has no fabricated extraction experiment.

The OpenRCX decomposition distinguishes continuous distance, native integer compute-grid/width mapping, and complete PEX. The extracted function-body hashes are recorded. Its FEM wrapper interpolates projected scalar components using the same S as every predictor. The third scalar channel carries the template diagonal component only, not native resistance. Native injection instead changes coupling/fringe and never changes resistance. Native return-value agreement and independent FEM errors are scored separately.

The all-support physical study retains the71 formal queries, six contexts,153 observations/context, original material/boundary contracts and independently certified labels. No label is used for slot generation, model selection or fallback. Full/Binary compute-table preparation uses all eligible finite slots, ordered by context/represented coordinate in blocks of32; these are newly scored predictions because changing Q can change attention outputs. Direct query scores and their completed Q1/8/32 timing experiment remain unchanged.

Coverage sensitivity includes every10/30/50/70% condition, five mask seeds and three protocols. S/Q is reconstructed from the frozen deterministic sampler and checked against every reused Full accumulator's scored indices. Binary and the new kernels use that exact S/Q. Full ensemble predictions are not replaced by mean-member scores. Actual counts, rank, complete-cell availability, fallback, hull regime and rounded duplicate identity are in `support_coverage_results.csv`. The source-selected GP is fixed by the prior validation receipt, not chosen on these query errors. Complete-cell subset scores are labeled separately; archived Full accumulators do not provide per-query predictions for a new subset, so no Full subset score is fabricated.

## Native preparation and timing

See `compute_table_integration.md`. The three required variants are original native, same-interface native-value pass-through and learned Full/Binary values. The additional disabled-hook executable control distinguishes binary/build effects. Full original characterization rules are unchanged for all these runs. This is a new deployment path, not the preceding B8 fixed-node rule export.

Every payload key binds process/corner, original rule/configuration SHA, model corner, pattern and layers, mapped width, slot index, represented separation, component pair and units. Policy hashes include frozen Full/Binary checkpoint identities. Whole sentinel tables, special/diagonal/resistance paths, unresolvable and non-held-out tables, and measurement-bin conflicts remain native. Initial/last-distance paths that directly return measurement entries remain native.

Inventories enumerate complete loaded rule grids. Equality between AES and Ibex inventories verifies that their coverage is not selected by observed design queries. The first inventory acquisition is nevertheless charged to cold preparation because this fixed public API reads rules only inside extraction. Full/Binary use all real support, never generated pseudo-observations. Pass-through payloads preserve exact native doubles through17-digit serialization.

A trace-only binary checks query ordering, mapped/returned geometry, injected values, all uncovered returns and resistance; electrical SPEF comparisons include full-net capacitance and resistance. Formal timing uses the release build without getter instrumentation, three seeded randomized passes of eight layouts and five modes (120 processes). PEX, native table construction, hook time, SPEF and STA are separately reported. Process wall residual includes startup/payload parsing and shutdown; it is not mislabeled isolated rule parsing.

First-design PEX overhead uses external preparation plus PEX and process residual versus the original executable. Inventory preparation includes its layout/library loading, rule registration, extraction/dump and process residual; diagnostic SPEF/STA performed by the inventory validation harness are separately recorded and excluded from algorithm preparation; the baseline PEX denominator excludes ordinary layout/library loading and STA. Warm overhead uses extraction only. Cold per-library estimates charge a complete model/input load; actual two-design reuse is also recorded, without arbitrary large amortization. Native tables are rebuilt inside each extraction process; populated payloads and source-model inference are reusable. Source training and support characterization costs from the preceding study remain separate supplied-input costs.

The machine is shared, with one inference/extraction thread pinned per worker, no fixed frequency or exclusive reservation. Builds use at most three LTO workers alongside at most one scoring worker; formal extraction benchmarks run after scoring completes. Existing experiments' runtime measurements are reused, not silently measured again. The new budget is16 CPU core-hours, at most four compute workers, no GPU or new field solving.

## Engineering checks

The first C++ compilation exposed private-field access; the hook now uses the public coupling/fringe setters and getters. Initial inventory then exposed `Array1D::set` not updating `getCnt`, with unused capacity uninitialized. The corrected hook reconstructs exactly the indices written by native mapExtrapolate/mapInterpolate and never walks spare capacity. Initial build/inventory logs are retained. The physical ideal-distance decomposition was corrected to retain native width mapping; its initial scores remain separately identifiable and are excluded from final summaries. These repairs do not change model weights, S, reference labels or the evaluation populations.

Inventory and validation initially shared diagnostic output paths. The original inventory timing CSV is retained; inventory acquisition was rerun into a separate directory and all slot dumps were verified identical before the formal 120-run benchmark. Its extra CPU cost is included.

`RESULTS.md`, `CHECKS.json`, the resource ledger and artifact manifest describe completed execution. Preparation, query replay, physical template evaluation, fixed-node export and computeTable injection retain distinct evidence identities.

## Authoritative manuscript and review archive

`paper/dac_layout_query_revision/main.tex` and `extended.tex` are the editable manuscripts. The migration template is used only once against the audited base; subsequent analysis runs preserve manuscript edits and update measured inputs. Do not rerun the older paper migration scripts against these sources. `sync_markdown.py` regenerates the reading copy and source/PDF hashes.

Run `python3 experiments/pex_kernel_revision/package.py` after committing to create a lightweight ZIP with the exact Git commit, relative paths and SHA-256 manifest. Payloads are losslessly gzip-compressed for distribution; full replay regenerates their TSV form. The archive contains this revision's compact raw results and the entire formal paper source tree; frozen earlier result dependencies are obtained from the recorded repository commit. It excludes weights, binaries, large SPEFs and getter traces.
