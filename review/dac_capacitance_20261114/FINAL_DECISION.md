# Final decision

**COMPLETION_ACCURACY_ONLY**

The new experiment supports conditional rule-completion and a measured cost/accuracy tradeoff. It does not establish a general characterization-efficiency advantage over strong equal-observation baselines, or universal necessity of full gating. Do not submit the planned broad efficiency/routing claim on this evidence alone. This is a completed bounded research revision, not an acceptance or submission-readiness claim.

## Gate 1: characterization efficiency

FEM B4 full NRMSE 0.1233 versus same-S adapted MLP 0.0515; at B8 0.0925 versus 0.0420. Transfer B4 is 0.1182 versus 0.0477; at B64 0.0386 versus 0.0264. Thus large advantages over the own anchor alone do not prove a characterization advantage over the strong learning control.

| Setting | Method | Error threshold | Reached trajectories | Not reached | Median B among reached |
| --- | --- | --- | --- | --- | --- |
| public | anchor | 0.1356 | 455/991 | 536 | 8.0 |
| public | affine | 0.1356 | 335/991 | 656 | 4.0 |
| public | gp | 0.1356 | 553/991 | 438 | 8.0 |
| public | mlp_adapt | 0.1356 | 734/991 | 257 | 4.0 |
| public | binary | 0.1356 | 944/991 | 47 | 4.0 |
| public | full | 0.1356 | 957/991 | 34 | 4.0 |
| reference | anchor | 0.2882 | 48/48 | 0 | 16.0 |
| reference | affine | 0.2882 | 48/48 | 0 | 8.0 |
| reference | gp | 0.2882 | 48/48 | 0 | 8.0 |
| reference | mlp_adapt | 0.2882 | 48/48 | 0 | 4.0 |
| reference | binary | 0.2882 | 48/48 | 0 | 4.0 |
| reference | full | 0.2882 | 48/48 | 0 | 4.0 |
| to_asap7 | anchor | 0.2908 | 24/24 | 0 | 16.0 |
| to_asap7 | affine | 0.2908 | 24/24 | 0 | 8.0 |
| to_asap7 | gp | 0.2908 | 24/24 | 0 | 8.0 |
| to_asap7 | mlp_adapt | 0.2908 | 24/24 | 0 | 4.0 |
| to_asap7 | binary | 0.2908 | 24/24 | 0 | 4.0 |
| to_asap7 | full | 0.2908 | 24/24 | 0 | 4.0 |


Thresholds are source-validation anchor-error quantiles, not application-certified tolerance requirements. Three data seeds per table are repeated observations, not independent technologies. The median is conditional on attainment and must be read with censored counts. Paired per-table comparisons, including one-sided/neither attainment, are in paired_attainment.csv. No extrapolation between budgets. Public accesses are simulated entries, so no measured field-solver saving follows. FEM costs are replayed original fine-only and coarse+fine+wide CPU records; no new solver wall speedup was measured. New training/target fitting costs are separate and historical source-pretraining CPU/GPU totals remain incomplete. No amortized total-cost superiority claim is licensed.

reference: at the frozen per-table threshold 0.28821552937419825, all 48 table/seed trajectories reach the threshold for both full and anchor. Their summed replayed fine-only CPU work is 1367.89 versus 3567.81 seconds. Full and adapted MLP instead require identical measured budgets in all 48 trajectories, with identical recorded characterization work. These sums count repeated experimental trajectories; they are not a unique PDK build cost.

to_asap7: at the frozen per-table threshold 0.2907519133283675, all 24 table/seed trajectories reach the threshold for both full and anchor. Their summed replayed fine-only CPU work is 765.41 versus 2005.59 seconds. Full and adapted MLP instead require identical measured budgets in all 24 trajectories, with identical recorded characterization work. These sums count repeated experimental trajectories; they are not a unique PDK build cost.

| Setting | B | Recorded fine CPU s | Recorded validated CPU s | Full completion s | MLP adaptation+completion s |
| --- | --- | --- | --- | --- | --- |
| public | 4 | unknown | unknown | 0.0076 | 0.4295 |
| public | 8 | unknown | unknown | 0.0077 | 0.4287 |
| reference | 4 | 28.50 | 65.80 | 0.0225 | 0.4974 |
| reference | 8 | 50.55 | 117.38 | 0.0230 | 0.4908 |
| reference | 16 | 101.81 | 236.94 | 0.0239 | 0.4832 |
| reference | 32 | 190.73 | 445.96 | 0.0250 | 0.4831 |
| reference | 64 | 370.21 | 867.02 | 0.0278 | 0.4846 |
| to_asap7 | 4 | 31.89 | 74.76 | 0.0220 | 0.5039 |
| to_asap7 | 8 | 57.40 | 135.01 | 0.0228 | 0.4791 |
| to_asap7 | 16 | 114.26 | 269.62 | 0.0236 | 0.4804 |
| to_asap7 | 32 | 215.45 | 510.48 | 0.0282 | 0.4843 |
| to_asap7 | 64 | 418.24 | 991.67 | 0.0274 | 0.4792 |


The CPU columns are mean recorded characterization work per table for the same support; completion columns are new wall measurements. They are not added into an end-to-end speedup.

## Gate 2: mechanisms and deployment

Observation conditioning and learned correction have useful scope relative to numeric anchors. The adapted-MLP result shows that target parameter fitting can explain much of the rank2 benefit. Full-versus-binary/residual differences vary with budget and setting; training-seed sensitivity and pointwise group bootstrap are separately available. All three source-validation comparisons rejected linear-only pruning under the registered strict error rule; its confirmation rows are labeled ablation, not selected deployment. No additional router search was performed. GP/anchor choices, routing, target adaptation and acquisition are separate factors.

Native full wins over CMI on net-C error in 16/16 and absolute WS deviation in 16/16 case/budget seed-mean cells. Against binary those counts are 6/16 and 4/16. All 240 budget native runs plus eight golden replays completed. Original 84 holdout tables include one ineligible short table, left golden; 83 eligible tables are changed identically across methods. Full-rule reference, R, layouts, SDC, libraries and executable hashes are fixed. Unmodified rule tables remain fully characterized for every method, so the budget is not a whole-PDK characterization budget. These are extraction/STA fidelity measurements, not chip performance, timing closure or signoff accuracy. Native failure coverage, P99 slack, TNS and endpoint/path/FN/FP results are retained.

## Gate 3 and stop

End state is COMPLETION_ACCURACY_ONLY. E1--E4, finite related-work adaptation, reverse direct-MLP transfer, correctness checks, plots and editable research paper are delivered. No further models, solver geometries or router searches are queued. Historical negative fixed-mask outcomes remain unchanged. The 770.07 CPU-second public execution failure and the administrative native scheduler handoff are explicitly archived. All original processes/data and publication artifacts were preserved; no remote push/publication/submission occurred.

AttentionCap is an official-backbone/head **adaptation**, not its original benchmark; component-only supervision and explicit boundary/material features are disclosed. Tsai comparison is a paper-inspired direct MLP, not the authors' original pipeline; their unseen-thickness capability is acknowledged. Flash-CNNCap remains a task-scope comparison, not a mismatched LUT-image experiment. General claims beyond these comparisons remain unsupported.
