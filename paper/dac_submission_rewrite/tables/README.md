# Derived tables and figures

- `fixed_missingness.csv`: all 15 process-domain/coverage conditions, exact mean-mask macro NRMSE. Original records are recomputed with the published aggregation; `fixed_missingness.tex` is the main table. `fem_gain_range.tex` derives unrounded FEM Full-versus-Binary reductions.
- `fixed_budget_all.csv`: every available reviewed method/budget row, including target observations, actual status, target fitting steps, wall-time scopes, and recorded FEM cost. `budget_aux.tex` supplies all feasible Ungated/CNP/adapted AttentionCap entries. Public AttentionCap dashes mean not run.
- `native_missingness.csv`: per layout/missingness/method, seed-mean net-C NRMSE and seed-maximum absolute WS/TNS errors. Includes all recorded methods even where the main figure focuses on CMI/Full. Original timing units are ns; plotted values are converted to ps.
- `native_budget.csv`: all 16 layout/budget conditions for CMI/Binary/Full and all retained native metrics, each already averaged over three data seeds. Slack and timing columns are ns, converted to ps in the figure. P99 is computed within a run before averaging. Native capacitance units are recorded in `cap_unit`.
- `support_protocol.csv`, `retention.csv`: individual-member, group-balanced scores. Equal-budget average is not an ensemble-prediction NRMSE.
- `geometry_example.json`: real recorded candidate coordinates, sealed Q, and ordered first eight support observations for data seed 11. No label acquisition or new sampling experiment.
- `component_family.csv`: pooled-replicate component-group scores for Full/Binary/GP/MLP. The optional `family_diagnostic.pdf` uses B4, averages those existing scores within family across defined process/components, and is separate from the self-contained main paper. Per-component values are retained in this CSV.

Missing normalized components are not replaced with zeros. The main manuscript's evidence and comparisons are readable without the optional family diagnostic.
