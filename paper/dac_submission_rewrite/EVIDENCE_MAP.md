# Evidence map for the formal submission rewrite

Starting research HEAD: `7334799ce7ca2e46dc4b4091b470cfc3af8c5cc7`.
Main: `05d0717c31c3ebd38107c846cfa7712913078027`, an ancestor of the research branch. The actual worktree was clean. No later changes needed merging. These branches contain one unpublished study; manuscript terminology follows scientific protocols, not repository chronology.

Only existing records were read. No training, model forward pass, model timing, solver, transfer prediction, extraction, or STA was executed. Derivations are performed by `build_figures.py`, using CSV/JSON/JSONL readers and an existing record-only aggregation function. It imports no experiment runner or model module. `INPUT_SHA256.json` records consumed inputs. Original results and previous manuscript directories remain unchanged.

| Claim / figure | Population and model state | Metric and record source |
|---|---|---|
| Method, Fig. 1 | Source-trained two-layer encoder; identical-input Full/Binary/Ungated; full-grid offline completion | `unified/{episodes,basis,model,train}.py`, `pdkcap/{interpolation,round2_model,round3_experts}.py`, `experiments/paper_controls/run_controls.py` |
| Data table | Public effective fitting/selection/confirmation 1051/246/340; budget eligible 338; FEM 16/24/16; transfer 8/12/8 | `docs/FINAL_PAPER.md`, `configs/paper_models.json`, model `FROZEN.json`, review `same_budget.csv`; inventory 1713 is not a test count |
| Fixed missingness, all 15 conditions | 30% masks; public, FEM, FreePDK15→ASAP7; three-member ensembles; original mask sequences | `experiments/paper_controls/scores/{public,reference,to_asap7}/{learned,baseline,affine}_confirmation.jsonl.gz`; `comparison_summary.json`; final table CSVs |
| Full gains over Binary in all five FEM conditions | Exact unrounded Full/Binary scores, not rounded CSV arithmetic | Record-only `scripts/verify_final_paper.py::aggregate`, equivalent process/family/component pooling per mask followed by mean over masks; regenerated Full values agree with source summary to <1e-12 |
| Fixed-budget curves and additional controls | Paired sealed Q; coverage sampling; data seeds 11/29/47; B4/B8 public; B4–64 FEM/transfer; original three-member ensembles | `review/dac_capacitance_20261114/same_budget.csv`, `results/dac_characterization_20261114/summary/{budget_curves,component_metrics}.csv`; `experiments/dac_characterization_20261114/summarize.py` and `pdkcap.metrics.summarize`: data seeds pooled before sqrt |
| Geometry coverage example | Real `r3-asap7-M7-DIAGUNDER`, 128 coordinates; recorded data-seed-11 B8 trajectory | `runs/round3_evaluation_inputs_v1/reference_confirmation_round3_main.jsonl`, `results/dac_characterization_20261114/confirmation_reference/records.jsonl.gz`; no new sampling/prediction |
| Fixed-missingness native | Eight fixed routed layouts × block 30/50%, three seeds; source-trained model | `runs/downstream_holdout_v1/summary.json`; checked `scripts/downstream_holdout_summarize.py`: net-C **mean** across seeds, WS/TNS **maximum absolute deviation** across seeds; no claim these are uniform metrics |
| Fixed-budget native | Eight layouts × B4/B8 × three seeds, 83/84 eligible holdouts; Full/Binary/CMI | `paper/dac_evidence_closeout_20261114/native_all_layouts_all_metrics.csv`, original `summary/downstream_raw.csv`; seed-mean net-C and timing errors; P99 within run then averaged |
| Native simple-gate and tail results | Same native conditions and original source-trained models, not H/L continuations | `paper/dac_evidence_closeout_20261114/{native_paired_deltas,native_delta_summary,native_compact}.csv`; error deltas relative to full-rule reference, not actual timing loss |
| Support-protocol analysis | Full/Binary × H/L × seeds 0/1/2, 2000 steps each; four process/layer dependency groups | `results/dac_support_mismatch_resume_20261114/EFFECTS_BY_SEED_BUDGET.csv`; closeout `mechanism_budget.csv`, `retention.csv`; mean-member, group-balanced metric, not ensemble predictions |
| Recorded component computation | Shared encoding + one forward, single-member Full-L/Binary-L | Closeout `completion_cost_ms.csv`; excludes claims about measured ensemble wall time or extraction speedup |
| CNP / adapted AttentionCap / reverse transfer | Actual finite selection and target fitting; no ANP run; no public AttentionCap matrix input | `learning.py`, `attention.py`, their `*_selection.json`; review `same_budget.csv`, `reverse_transfer.csv`; adapted AC uses component supervision, not full-matrix labels |

The source record's supported normalized score excludes zero truth energy; zero components remain in absolute diagnostics. Different protocol panels retain their own aggregation; no cross-panel percentage reduction is computed. The fixed-missingness baseline list uses its original kernels and source-selected affine rule, not the differently selected budget GP.

## Manuscript and reviewer inputs

The original `paper_checked.pdf` was extracted and consulted for its task framing, method, original tables, and implementation details. Its generic chip-flow/waveform illustration is replaced by the actual completion/export interface. The task brief supplies the key concerns attributed to Y7Hm, kFJA, and u6Cs. The individual three reviewer screenshots were not identifiable in the supplied repository paths; their summarized concerns in the brief, rather than invented quotations, inform the rewrite: simple matched controls, local affine and target-fitted alternatives, support conditions, nearest conditional-regression work, and native tails. No claim is made to have inspected missing screenshots.

## Primary literature and venue checks

Verified official DAC submission page and technical topics; primary AttentionCap and Flash-CNNCap arXiv full texts and official repositories; OpenRCX calibration documentation; Tsai author page; ResCap ASP-DAC official program abstract; Hybrid PEX institutional author record; CNP PMLR and ANP arXiv. Tsai's hosted PDF returned HTTP 502 in the browsing interface, so input/output claims were checked against the author's detailed page and the repository's existing study description. No claimed reproduction of its proprietary extraction implementation.

- https://dac.com/2027/program/research-manuscript-submissions
- https://dac.com/2027/program/research-topics
- https://openroad.readthedocs.io/en/latest/main/src/rcx/doc/calibration.html
- https://arxiv.org/html/2606.08161v1 and https://github.com/THU-numbda/AttentionCap
- https://arxiv.org/html/2607.23877v1 and https://github.com/THU-numbda/flash-cnncap
- https://mike84265.github.io/research/ml_pex.html
- https://tsys.jp/aspdac/2025/program/program_abst.html
- https://fount.aucegypt.edu/faculty_journal_articles/4632/
- https://proceedings.mlr.press/v80/garnelo18a.html
- https://arxiv.org/abs/1901.05761

IEEEtran.cls is an unmodified local IEEE conference class; IEEEtran.bst is the official CTAN distribution. Both retain their distribution notices.
