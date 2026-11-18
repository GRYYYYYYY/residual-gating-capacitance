# Reconstruction and provenance

The parent manuscript, its PDF, bibliography and Overleaf package are the tracked files in paper/dac_layout_query_main13_restored at b98f41aa12e06d6c7ce80ed7eb3db6c1f3630a4b. The legacy extended source at that commit is paper/dac_layout_query_revision/extended.tex. Git compares the two editions by path and commit. The edition in this directory incorporates complementary extended evidence without duplicating the common manuscript.

From the repository, run the commands below from this directory. Building only the PDF requires the corresponding source package and a standard LaTeX installation with pdfLaTeX, BibTeX and latexmk. The audit program reads evidence from the repository separately.

~~~sh
bash build.sh main
bash build.sh extended
python3 verify_evidence.py
python3 package_paper.py
~~~

The package places main.tex and extended.tex at its root. Select the desired main document in Overleaf and use pdfLaTeX. The archive contains the cited bibliography, local class/style files and actual figure/table inputs. The packaging script builds the two targets in separate empty directories and compares text, font embedding and rasterized pages with the revision PDFs.

## Claim and exhibit mapping

Paths below are relative to the repository root. In the table, P denotes paper/dac_layout_query_revision, K denotes results/pex_kernel_revision, R denotes results/runtime_accuracy_20261115 and A denotes results/dac_main13_integrated_revision/main13_20261117. Coverage totals for individual variants, support regions, ratios and protocols are available numerically.

| Manuscript item | Primary record or implementation |
|---|---|
| Workflow and supported kernels, Figs. 1–3 and Algorithm 1 | K/baseline_contracts.json, extracted_native_validation.json, injection_contract.json, pinned_storage_retrieval_checks.json, pass_through.json, inventory/, validation/. Schematic assets are carried from the restored baseline. |
| Eight-layout census, raw/effective nodes and occurrence weighting | results/layout_offgrid_20261115/query_manifest.jsonl.gz, K/query_census_by_layout.csv, census_plot_source.json, census_plot_queries.jsonl.gz, census_plot_knots.csv |
| Geometry and material tokens, scales, sample order and interactions | unified/episodes.py, unified/queries.py, unified/basis.py, unified/model.py, unified/train.py, pdkcap/interpolation.py, pdkcap/round2_model.py, pdkcap/round3_support.py, pdkcap/round3_experts.py. A/query_batching_tests.json and query_batching_error_changes.csv record batch effects. |
| Section IV and Table I | A/data_count_mapping.csv, source_initializers.csv, training_opportunities.csv, experiments/paper_controls/data_audit.json. Raw and canonical observation populations refer to different manifests. |
| Fig. 4, absolute coverage, margin, dependence and controls | K/coverage_{public,reference,to_asap7}.jsonl.gz and coverage_inventory_*.csv, P/trials/fig4_ungated_20261116T230943, P/tables/coverage_with_ungated.csv, A/baseline_dominance_summary.csv, baseline_uncertainty_summary.csv, mechanism_selected_cases.csv, mechanism_summary.csv, mli_status_reconciliation.json. The separately trained gates and source-fitted fixed mixture are documented in docs/dac_main13_integrated_revision/mechanism_attribution.md. |
| Fig. 5 and extended budget/continuation/transfer findings | P/data/fixed_budget_bars, P/tables/fixed_budget_all.csv, budget_aux.tex, numerical_30percent.tex and support_protocol.csv, A/fixed_budget_controls.csv, results/dac_characterization_20261114 and results/dac_support_mismatch_resume_20261114. The reverse-direction experiment is separate from the main transfer cohort. |
| Independent physical queries and certified reference | K/physical_mapping_contract.json, physical_predictions.jsonl.gz, physical_checks.json, physical_summary.csv, physical_geometry_effects.csv, K/ideal_decomposition_correction.json. Numerical service and solver costs use R/accuracy_runtime.csv, solver_timing.csv and supplied_input_costs.json. |
| Fixed-node export, Table II left, Fig. 6 | P/build_downstream_two_kernels.py, P/data/downstream_two_kernels/{native_metrics.csv,spatial_seeds.csv,spatial_summary.csv,verification.json}, per-endpoint seed means and raw bundles there and in P/data/downstream_matched_mli. P/tables/native_missingness.csv, native_budget.csv and rule_export_absolute.tex give the additional downstream controls. |
| Full-support compute-table measurements, Table II right | K/deployment_summary.csv, native_flow_timing.csv, prepare_timing.csv, inventory_cost.csv, preparation.json and pass_through.json. The underlying number of release runs is 120, including originals. |
| Matched sparse-native results | A/native_sparse_metrics.csv, native_sparse_cell_means.csv, native_sparse_win_counts.csv, native_coverage_summary.csv and tests/. The hidden-label and four-arm interface protocol is in docs/dac_main13_integrated_revision/native_sparse_report.md. |
| Warm timing, fitting, fixed-node preparation and extraction | R/PROTOCOL.json, timing_raw.csv.gz, accuracy_runtime.csv, cold_load.json, native_flow_timing.csv, rule_preparation_summary.csv, deployment_cost.json and PAPER_VALUES.json. The 96 fixed-node release runs have an independent original-rule denominator. |

The detail directory copies typeset tables from P/tables and the corresponding six plots from P/figures. For query_errors the package uses the sibling 2000 × 520 PNG exported by the same plotting run. The archived PDF embeds a Type 3 font. All detail assets are byte-identical to their source counterparts. The displayed data can be compared directly to the baseline files of the same names. The new build reads only tables/downstream_merged.tex from the restored table directory. Its generator joins the archived two display inputs without changing the metric values. The scientific report gives the independent checks on the aggregation behind these displays.
