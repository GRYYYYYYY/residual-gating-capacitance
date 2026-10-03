# Final-paper alignment

The final manuscript is **Chip Capacitance Prediction by a Jointly Routed Transformer** ([PDF](../paper/paper.pdf), [source](../paper/main.tex)). `paper/manifest.json` identifies the exact copied final artifacts. The final main text and figures occupy nine pages; references and appendices follow.

## Scope and mapping

| Paper location | Repository implementation / evidence |
|---|---|
| Section 3, Method | `unified/episodes.py`, `unified/model.py`, `unified/train.py`, `unified/score.py` |
| Structured tokenizer | Geometry, material context, observation indicator/value and support anchor in `unified/episodes.py` |
| Joint residual and component routing | Shared encoder, neural residual and learned mixture in `unified/model.py`; masked query loss in `unified/train.py` |
| Tables 1–2 | `paper/tables/main_completion.tex`, `paper/tables/main_transfer.tex`; `configs/paper_models.json`; raw 30% baseline and model records under `experiments/paper_controls/scores/` |
| Table 3 / Figure 3 | `paper/tables/main_downstream_compact.tex`; four-panel horizontal figure in `paper/sta_visualization/gf180_ibex_50/figures/` |
| Appendix E: matched controls and affine extrapolation | `experiments/paper_controls/`; 18 trained control members, three settings, two variants, three seeds |
| Data fitting / selection / confirmation | `experiments/paper_controls/data_audit.json`, `database/catalog.json`, original run receipts |
| Full historical numerical provenance | Immutable v1.0.0 downloads and `results/expected_tables/` (not final-paper layout/scope) |

The final paper reports public rules, FEM reference, and **FreePDK15 → ASAP7** transfer. It does not include ASAP7 → FreePDK15 in the headline denominator. `configs/paper_models.json` is the final three-setting mapping; `configs/selected_models.json` retains the original four-setting archive for compatibility.

## Counts and source-only selection

| Setting | Fitting | Model selection | Confirmation |
|---|---|---|---|
| Public | 1,051 unique tables after deduplication and downstream holdout | 246 unique holdout-view validation tables | 340 unique tables in the original confirmation view |
| FEM | 16 original tables, 153 nodes each | 24 separately generated validation tables | 16 Round-3 tables, 128 nodes each |
| FreePDK15 → ASAP7 | 8 FreePDK15 tables, 153 nodes each | 12 FreePDK15 tables | 8 ASAP7 Round-3 tables, 128 nodes each |

Raw inventory counts and effective loader counts differ. The public inventory contains 1,713 rows; the downstream holdout view has 1,061 train and 247 validation rows before `unique_tables`, giving 1,051 and 246 effective tables. The 84 downstream tables are excluded from fitting and validation; the downstream model is evaluated on the separately recorded public confirmation view. These views must not be added as independent samples. The Round-3 FEM collection has 27 tables (16 confirmation, eight validation, three boundary); this collection is not the 16-table fitting set or the complete 24-table selection cohort.

ASAP7 target labels are not used for model/hyperparameter selection in the reported transfer. Older tables labeled “ASAP7 val.” referred to the **to-ASAP7 setting's source validation**, which contains FreePDK15 only. Final-paper text uses source-validation terminology. Available target observations are permitted inference inputs; withheld target queries remain unavailable.

## Interpretation and limitations

CMI is a transparent, rank-matched commercial-style multilinear control; the code does not identify proprietary commercial algorithms. Extrapolation is relative to the observed support, not necessarily outside the source training distribution. Numerical comparisons alone do not establish a benefit from complex routing. The final appendix therefore includes identical-input, matched-budget ungated and binary-gated Transformers, plus validation-selected local affine extrapolation.

Full routing is better than the ungated model in 14/15 and the binary gate in 13/15 conditions. Public gains are small and several paired confidence intervals cross zero; two transfer conditions favor binary routing. Local affine wins the out-of-support random FEM and transfer conditions. Removing several analytic branches changes public NRMSE by less than 0.5% while substantially reducing scoring time. The manuscript reports these limitations explicitly.

## Reproduction boundaries

- `python scripts/verify_final_paper.py` verifies the manuscript asset hashes, final scope, and recorded score aggregation; it does not rerun training or STA.
- [Control reproduction](../experiments/paper_controls/README.md) regenerates supplementary tables and supplies fresh training and scoring commands.
- `python scripts/reproduce_reports.py --sta ...` reproduces the **historical 39-table v1.0.0 release**, preserving its checksums and reverse-transfer results. It is not a claim to regenerate the final LaTeX formatting.
- Full-model inference, data download, solver provenance and saved-layout STA replay remain described in [REPRODUCING.md](REPRODUCING.md).

Compile the manuscript with `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex` from `paper/` (TeX Live with `float`, `wrapfig` and the supplied conference style). Generated build files should not be committed.
