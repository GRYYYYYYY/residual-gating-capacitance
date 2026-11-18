# Editorial and scientific triage before revision

Reviewed the restored main source and its eight-page PDF at b98f41aa12e06d6c7ce80ed7eb3db6c1f3630a4b, its figures, input tables, bibliography and ZIP, and the separate extended source and evidence tables in ../dac_layout_query_revision. The new worktree starts at the identical local and upstream revision head. The original checkout contains additional untracked material and stays intact. The table below gives baseline locations, impact and the evidence required for correction.

| ID | Location | Priority and issue | Correction and evidence |
|---|---|---|---|
| S1 | II-B, Fig. 2 | P1. Raw requests, effective bins and writable slots have different denominators. Exclusions appear only as a comment. | Sum eight getter census rows and distinguish native slot eligibility. |
| S2 | II-C, III-B | P1. Projected interpolation and full-space support classification can disagree. Rank zero and rank-one boundary behavior are underspecified. | Trace interpolation.py and round2_model.py. |
| S3 | III-A, Algorithm 1 | P1. Support-first ordering describes native batches, not arbitrary evaluation episodes. | Trace episodes.encode and the native prediction adapter. |
| S4 | III-B | P1. Expert dimension, scale, initial priors and validity depend on the model configuration. | Check forward pass, frozen receipts, width and GP implementations. |
| S5 | IV-A, Table I | P1. Effective cohort counts sum to 76 fewer than the raw inventory. | Reconcile split-specific holdout removals and duplicate rows. |
| S6 | II-C, V-A | P1. Complete MLI coverage differs between archived aggregate and corrected recount. | Preserve the primary error scores and identify the support accounting separately. |
| S7 | V-A | P1. Win counts alone obscure the magnitude and dependence of errors. | Reaggregate the frozen 60 cells, including all unfavorable cells. |
| S8 | V-B | P1. Table confirmation, transferred labels and independent template reference describe distinct populations. | Separate physical construction and fixed-budget adaptation, retain numerical wins. |
| S9 | V-C, spatial map | P1. Endpoint range lacks estimator, join and denominator. Worst-slack and P99 conclusions differ. | Check seed-level spatial records and endpoint data, both protocol-specific references. |
| S10 | IV-C, V-C | P1. Rule export and compute-table injection charge different preparation and extraction stages. | Read cold accounting, native and fixed-node timings, include unfavorable IHP results. |
| E1 | Abstract, I | P1. Background, research gap, default selection and contribution statements repeat. | Reconstruct the introduction from workflow through deployment, shorten abstract. |
| E2 | II-D | P2. Task interfaces and adaptation are interleaved. | Group papers by inputs and outputs and move adaptation settings to IV. |
| E3 | III | P2. Several hundred lines of superseded method text remain commented. | Remove stale code after tracing each active equation and algorithm operation. |
| E4 | III--IV | P1. Source episode loss and target fitting lack a common explanatory boundary. | Define source objective in III and report opportunities in IV. |
| E5 | V | P2. Results begin inside the first experiment. | Introduce the questions and organize by evaluation protocol. |
| E6 | Table II | P2. Two labels refer to one combined table. | Use a single label, clarify reference and timing units. |
| E7 | Bibliography | P2. Two entries point to the same OpenRCX runtime manual. | Deduplicate, distinguish vendor documentation from scientific sources. |
| E8 | VI | P2. Conclusion largely repeats abstract. | State operating conditions, independent reference result and engineering implication. |
| E9 | Extended | P1. Different title, method exposition and figure organization can diverge. | Share revised six-section text and add evidence only in extended build. |
| E10 | PDF | P0. Baseline exceeds DAC body limit. | Retain main equations, algorithm and results. Move granular supporting records into extended version. Check each page and independent rebuild. |

DAC 2027 specifies six body pages and one references-only page. [Research track instructions](https://dac.com/2027/program/research-manuscript-submissions)
