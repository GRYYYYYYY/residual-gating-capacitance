# Internal compute-table interface

The implementation patches an isolated copy of pinned OpenROAD `0b54bb3203e0895f87940ff982358a6e4d406e28`, retaining the original installation and archives. `build_native.py` records the exact commands and source diff. `extDistRCTable::readRules` calls the hook immediately after `interpolate(4,-1,rcPool)`, during rule loading, before extraction getter calls. This is distinct from the existing fixed-node rule-file export.

The key identifies process, typical corner, original rule SHA and preparation-policy hash, model corner index, pattern family, metal and lower/upper context, mapped integer width, compute-grid index, represented separation, component pair and internal units. Every payload has its own SHA including predictions; model identities remain frozen. Query coordinates use the represented slot separation, not merely the raw request or nominal slot-index multiple.

Only finite, non-sentinel OVER/UNDER/OVERUNDER tables whose complete measured samples uniquely resolve to a source-held-out rule are eligible. We retain every actual characterization value. Entire special-tail tables, diagonal/resistance read paths, unresolved tables, source-fitting tables, and inadequate supports remain unchanged. A compute slot sharing a bin with a measurement is protected even if the represented coordinate differs. Initial/last-boundary getter paths continue returning `measureTable`; their behavior is not claimed to change.

Only `setCoupling` and `setFringe` write data; resistance, all measurement nodes, other fields, object pointers and downstream assembly remain native. The release build has no getter instrumentation; a separate trace build validates returned values and resistance. Native-disabled, native-value pass-through, Binary and Full use the same interface. Original-release runs are an additional executable-level control.

Preparation enumerates the full eligible finite grids and sorts their represented coordinates, using all real S with Q chunks of at most32 and three members. Predicted slots never enter S. The layout is not used to select slots. Inventories from AES and Ibex must match within each process before marking the cache reusable. Since this pinned Tcl interface defers table loading until extraction, inventory acquisition runs one extraction and its cost is explicitly charged to cold preparation; no fictitious free rule-only API is assumed.

Native-return and SPEF equality verify interface preservation, not field accuracy. Same-FEM-support evaluation separately uses the extracted pinned width/grid/getter function bodies with a declared scalar projection wrapper, scores all71 templates, and checks learned slot generation and retrieval. This does not align the commercial/native calibration stack with the two-dimensional FEM template.

Actual completion and counts are generated from execution receipts into `RESULTS.md`; this document specifies the interface, not a substitute for those receipts.
