# Claims and scope

Global judgment remains COMPLETION_ACCURACY_ONLY. This is an editorial closeout of completed evidence, not another experiment. Paths below are relative to the repository.

| Claim | Disposition | Direct evidence | Boundary |
|---|---|---|---|
| Equal-observation numerical, conditional and target-adapted rule completion can be compared reproducibly | Retain | results/dac_characterization_20261114/summary/budget_curves.csv; review/dac_capacitance_20261114/same_budget.csv; original evaluate.py | Same S/Q, not equal source tuning/training opportunities across all models |
| Target adaptation and simple gates are competitive | Retain | E1 table; historical adaptation-plus-completion records | Combined times are not pure adaptation latency; old ensemble E1 is not M |
| Full-L has a local four-budget mean advantage | Retain, explicitly narrow | mechanism_budget.csv from EFFECTS_BY_SEED_BUDGET.csv | M, mean individual-member errors; 3/3 seeds; 4.23% relative to mean binary-L NRMSE, not MAPE |
| Low-support training uniquely benefits Full or creates its advantage | Delete | I negative in all seeds; gap narrows from0.014088 to0.002939 | Binary responds more strongly; Full D positive in2/3 |
| Full-L is best at all budgets | Delete | mechanism_budget.csv, original per-seed file | Binary-L wins B4 in3/3, B8 in2/3; Full-L loses to Full-0/H at B16/B32 |
| Low-support protocol is a uniform fix | Delete | retention.csv, budget table | Original-support retention costs and larger-budget degradation remain |
| Pure support-count causality or independent confirmation | Delete | frozen paired episode protocol and MECHANISM_REPORT | Count and geometry coverage change together; known cohort, four groups and three fixed seeds |
| Full computation is free or broadly accelerates extraction | Delete | completion_cost_ms.csv; source_continuation_cost.csv | Encoding+one forward CPU estimates; no new ensemble wall, solver or native timing |
| Native interface improves fidelity versus CMI | Retain | native_all_layouts_all_metrics.csv; same-batch downstream_raw.csv | Eight layouts,83 replaced tables, unchanged remaining rules, full-rule reference; no silicon/signoff truth |
| Native Full universally improves on binary | Delete | native_paired_deltas.csv; native_delta_summary.csv | Net C6/0/10, WS4/0/12, P99 slack6/0/10; include TNS/FN/FP and overlap/rank metrics |
| Capacitance tail superiority | Narrow | TAIL_PAIRED_DIFFERENCES.csv |887/225/616 lower/tied/higher correlated cells; distinct from STA P99 |
| Whole-process savings, broad transfer or repaired downstream tails | Not established | original decision, scope and absence of corresponding new measurements | No new experiment is run or proposed as an automatic follow-up |
| Complete publicly downloadable reproduction assets | Do not claim | existing git files and LARGE_ARTIFACTS/CHECKPOINT_LINEAGE path/hash references | Local paths/hashes do not prove public availability; no weights/data newly published |

Input hashes in INPUT_SHA256.json pin the exact material read. The manuscript's main native table aggregates first over three seeds within layout, then eight layouts; the supplement retains all layout values and reviewed metrics. Original negative results and failed-attempt records remain unchanged in their existing directories.
