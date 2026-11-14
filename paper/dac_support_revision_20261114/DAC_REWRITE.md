# Support-Conditioned Completion of Capacitance Rules for Parasitic Extraction

Research revision for a DAC-oriented evaluation. End state: **COMPLETION_ACCURACY_ONLY**. This manuscript does not claim submission readiness.

## Abstract

We study offline completion of capacitance rules from a limited number of target-process geometry observations. The output is a native rule file consumed by an unchanged parasitic-extraction and static-timing flow. We evaluate a support-derived numerical anchor, conditional residual models, full numerical/neural fusion, and equal-observation numerical and learning controls on a fixed sealed query population. The protocol distinguishes simulated rule accesses, replayed finite-element characterization CPU cost, and newly measured prediction and adaptation time. The public cohort admits only budgets 4 and 8 for 338 eligible tables. On finite-element and FreePDK15-to-ASAP7 cohorts, target-adapted direct regression is a strong counterexample to universal full-gate efficiency: at four observations, its NRMSE is 0.0515 and 0.0477, compared with 0.1233 and 0.1182 for full fusion. We additionally evaluate a component-supervised adaptation of official AttentionCap and native extraction/STA on eight fixed layouts. The evidence supports a bounded rule-completion study and an adaptation-versus-inference tradeoff, but not a general characterization-cost advantage or universal necessity of complex gating.

## 1. Introduction

Parasitic extraction commonly reuses a characterized geometry-to-capacitance rule library. Building this library and filling gaps in its geometric coverage are separate from applying it to a routed layout. Existing observations within a target table carry process-specific information that can be provided at inference or used for parameter adaptation. The practical question is whether that information improves a completed rule library at the same reference-query budget, or reduces the number and cost of queries needed for a declared error level.

Our deployment is offline: select and purchase target geometries, complete a fixed candidate grid, export native rules, then run existing OpenRCX and STA. This scope makes input ownership and costs explicit. We do not replace the entire extractor, learn resistance, reconstruct arbitrary three-dimensional Maxwell matrices, or claim silicon/signoff accuracy. Query extrapolation refers to current observed support; it need not exceed source-training geometry coverage.

The contribution is a reproducible, budget-accounted evaluation of support-conditioned rule completion and its native interface. A residual around a numerical anchor is a useful design, but the scientific question includes simpler residual/binary models and target-adapted direct learners. We report their failures and strengths rather than attributing every improvement over interpolation to complex fusion. Three-seed model ensembles, immutable query sets, original solver receipts and native fixed-layout runs allow the claims to be checked independently.

## 2. Related work and comparison scope

AttentionCap learns capacitance matrices from conductor geometry using a Transformer and a Laplacian head [1]. We reuse the official implementation on the common reconstructible FEM geometry, adapting its input representation for material layers and the external ground boundary. Supervision is restricted to the same three components available to all methods. This is an adapted baseline, not a reproduction of the authors' original dataset or reported error. Flash-CNNCap maps three-dimensional windows to contribution images and reconstructs capacitance matrices/netlists [2]. Its window and DEF-to-SPEF task differs from fixed-grid rule completion; we neither convert LUT sequences to artificial images nor claim numerical superiority over its complete extractor.

Tsai et al. encode geometry and layer thickness for interconnect exploration and demonstrate unseen-thickness prediction without repeated per-thickness retraining [3]. Our direct MLP is a paper-inspired implementation using the available coordinates and structural/material summaries, with finite learning-rate selection and equal-support target adaptation. It does not reproduce their full pattern extraction or layout assembly. Within-stack thickness generalization is distinct from cross-stack adaptation.

ResCap already combines a physical estimate and a learned residual [4]. Accuracy-Based Hybrid PEX selects among rule, neural and field-solver methods according to accuracy needs [5]. CNP/ANP establish conditioning on observed context sets [6,7], and AIL-DNN addresses adaptive incremental learning [8]. We do not claim first use of residual learning, hybridization, observation conditioning or adaptive sampling. Our empirical distinction is the frozen information budget and native rule-library fidelity evaluation. All reported comparisons use our matched physical definitions and NRMSE; numbers from unrelated papers are not assembled into a cross-paper ranking.

## 3. Problem and extraction interface

For a table with candidate geometries X and permitted context c, let S be purchased indices and y(S) their capacitance vectors. A predictor computes F(X,c,S,y(S)) on the entire fixed grid. The evaluator seals Q, disjoint from the candidate pool from which S can be selected. Q is unchanged across budgets, methods and sampling trajectories for a table/data seed. Unqueried candidate labels are also hidden. Source-trained normalization is fixed. Candidate and query geometry are permitted transductive inputs; invariance to a changed query set or online single-query deployment is not assumed.

A budget unit is one unique geometric reference query, including initialization. One geometry may return several components and require multiple conductor excitations; those components do not multiply the query charge. We report the excitation work separately. Repeated queries use a declared cache and cannot reveal a label before being charged. Public-rule accesses simulate observations of existing source-rule values. FEM labels derive from a two-dimensional material-stack cross section with infinite extrusion, not a general three-dimensional window.

Public outputs are coupling and ground capacitance in source-rule-native per-length units. Their 1,713 tables all have rank-one geometry variation. FEM outputs, in F/m, are summed two-sided lateral coupling, ground including both the external boundary and explicit grounded context, and diagonal coupling. Independent width and spacing parameters make the FEM grid rank two; parameter dimension and field dimension are different concepts.

The exporter substitutes only unobserved capacitance tokens on eligible held-out rows and preserves observed rows, comments, other rule rows and resistance. Of the original 84 downstream holdouts, one has insufficient points for the shared sealed-Q protocol and remains golden; 83 are eligible. All methods use this identical subset. The resulting rule file is consumed by native OpenRCX on the same routed/connected database, SDC, cell libraries and executable. Reference timing comes from the full original rule file. Other rule tables retain their already available golden values for every method. Thus the native budget applies to these selected held-out tables, not to rebuilding an entire PDK from scratch; public fitting also contains other tables from the same processes.

## 4. Method and alternatives

The support anchor is computed from S and y(S). A shared Transformer encodes geometry, structural/material context, observed values, an observation indicator and the anchor. Its residual head predicts a correction. The full model combines numerical corrections and neural raw/clamped corrections with component-wise weights, then applies nonnegativity and restores observations exactly. Classical options include PCHIP, aligned-width interpolation and six RBF-GP configurations: length multipliers 0.5/1/2 with ridge 1e-6/1e-4. The anchor is a separate control because it differs from rank-matched multilinear interpolation on sparse rank-two grids.

Full inference evaluates applicable branches before fusing them. Low gate weight does not automatically avoid branch computation. Ungated residual and binary anchor/neural controls reuse the original fitting data, warm start, architecture core, optimizer budget and three training seeds. Their actual local weights were verified and reloaded; historical fixed-mask scores were not reused as budget predictions. A linear-only dictionary mask is evaluated as a separately labeled pruning ablation. All three registered source-validation comparisons favored retaining the full dictionary under the strict error selection rule.

Other controls are explicitly implemented rank-matched multilinear interpolation, validation-selected local affine, an independently selected GP, PCHIP where applicable (anchor fallback on rank-two tables), a direct MLP, and a deterministic mean-aggregation CNP. Direct MLP target adaptation uses only the same purchased S; no early stopping or free calibration label uses Q. Zero-target MLP and AttentionCap predictions are clearly information-limited controls. The anchor-conditioned method has no defined empty-support interface and is not assigned a fabricated zero-observation result.

## 5. Experimental protocol and cost accounting

Effective public fitting/selection/confirmation counts are 1,051/246/340; FEM counts are 16/24/16; FreePDK15-to-ASAP7 counts are 8/12/8. All 84 downstream tables and duplicate content are absent from public fitting and selection. Confirmation cohorts have been used previously, so this is a new protocol on existing confirmation data, not a new blind test. Three published full members per setting and 18 matched-control members pass checkpoint hash and configuration checks.

The inherited numerical evidence retains 14,688 initial, 11,016 expanded-coverage and 10,368 boundary receipts. Mesh/boundary convergence, flux-energy consistency, reciprocity and matrix checks pass their recorded criteria. The analytic coaxial pilot has relative error 0.00026334. These checks support the declared numerical reference; mutual consistency alone is not an external three-dimensional or silicon signoff validation. No new field-solver experiment is claimed in this study.

Budgets are 4/8/16/32/64, filtered by candidate-pool size. Three data seeds 11/29/47 define fixed Q (20% with at least two points for ordinary tables). Four geometry-coverage points initialize each trajectory and count toward B. A common two-point rule applies to tables with four to seven nodes; tables with fewer than four are ineligible for every method. Public confirmation has 338 eligible tables at B4/B8 and none at B16 or larger. Primary comparisons share geometry-coverage S; random and curvature comparisons share Q and initialization but may select different later S.

Primary macro NRMSE pools squared error and squared truth within process/family/component, then averages the defined component ratios. Native MAE and table P95/P99 absolute errors accompany it. No weak-capacitance observations are removed. All-zero truth components remain in absolute metrics and are excluded only from undefined relative normalization. Failures and unavailable budgets remain explicit. Group bootstrap uses 2,000 paired resamples of dependency groups within process; repeated data seeds and all families of one FEM layer stay together. These are pointwise intervals, not uncertainty over a broad population of process technologies. Training-seed variation is reported separately at fixed data seed 11.

Two learning rates and a fixed 3,000-update endpoint are offered to new MLP/CNP and adapted AttentionCap controls; source validation selects the candidate, followed by training seeds 1/2. Target adaptation candidates are 0/50/200 updates, selected on source validation only. Local affine reuses the earlier validation choices 4/8/8. Independent GP selection uses the six registered configurations. The new MLP/CNP source sampler balances families and samples tables uniformly within family; it does not match the archived process-balanced sampler or its longer training schedule. Therefore only the archived full/residual/binary controls are matched in training budget. New models match source data and target observations with a finite selection opportunity, not globally optimized performance. No confirmation-driven router search or unbounded correction round is performed.

Error thresholds are the first, second and third quartiles of source-validation anchor table errors at B8 (or the largest feasible smaller budget). They are descriptive thresholds, not application-certified tolerances. We report the smallest measured budget attaining each threshold, preserving non-attainment rather than extrapolating an unmeasured budget. Costs distinguish unique geometry queries, original fine-only CPU work, original coarse+fine+wide validated CPU work, and measured completion/target-fitting/selection/export/native time. The 12,024 geometry-index entries link to original solver records and exact fine-matrix projections. Cached charged wall time is not substituted for characterization work. Historical source CPU/GPU cost is incomplete; no total-cost or real solver wall-speedup claim follows.

## 6. Results

### 6.1 Fixed-budget completion

| Setting | B | cmi | anchor | affine | gp | mlp_adapt | cnp | residual | binary | full |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| public | 4 | 0.4229 | 0.4229 | 0.4266 | 0.3887 | 0.2860 | 0.2650 | 0.0776 | 0.0793 | 0.0708 |
| public | 8 | 0.3689 | 0.3689 | 0.3532 | 0.4013 | 0.2599 | 0.2374 | 0.0682 | 0.0648 | 0.0609 |
| reference | 4 | 0.2670 | 0.3391 | 0.2602 | 0.2767 | 0.0515 | 0.2356 | 0.1100 | 0.1315 | 0.1233 |
| reference | 8 | 0.2296 | 0.2752 | 0.2253 | 0.1633 | 0.0420 | 0.2313 | 0.0917 | 0.0947 | 0.0925 |
| reference | 16 | 0.1687 | 0.1525 | 0.1709 | 0.0543 | 0.0316 | 0.2297 | 0.0681 | 0.0565 | 0.0409 |
| reference | 32 | 0.1011 | 0.0942 | 0.0986 | 0.0354 | 0.0252 | 0.2274 | 0.0657 | 0.0537 | 0.0332 |
| reference | 64 | 0.0685 | 0.0444 | 0.0615 | 0.0280 | 0.0248 | 0.2271 | 0.0609 | 0.0491 | 0.0250 |
| to_asap7 | 4 | 0.2640 | 0.3358 | 0.2572 | 0.2734 | 0.0477 | 0.2138 | 0.1410 | 0.1153 | 0.1182 |
| to_asap7 | 8 | 0.2261 | 0.2698 | 0.2217 | 0.1584 | 0.0366 | 0.2126 | 0.1282 | 0.0961 | 0.1034 |
| to_asap7 | 16 | 0.1662 | 0.1500 | 0.1682 | 0.0526 | 0.0310 | 0.2135 | 0.1069 | 0.0762 | 0.0685 |
| to_asap7 | 32 | 0.1005 | 0.0897 | 0.0969 | 0.0341 | 0.0272 | 0.2127 | 0.0954 | 0.0700 | 0.0495 |
| to_asap7 | 64 | 0.0675 | 0.0435 | 0.0601 | 0.0271 | 0.0264 | 0.2136 | 0.0814 | 0.0611 | 0.0386 |


At four FEM observations, full fusion improves over the anchor but loses to the same-support adapted MLP. The difference persists through the low and middle budgets. For transfer at B64, full is 0.0386, GP is 0.0271, and adapted MLP is 0.0264. These controls prevent interpreting an interpolation comparison as evidence that complex fusion is uniquely data efficient. Full inference avoids target optimizer updates, while the MLP pays a measured fitting cost; completion_cost.pdf presents this separate tradeoff.

Public results are restricted to the feasible rank-one cohort. At B4, full/binary/anchor NRMSE is 0.0708/0.0793/0.4229; at B8 it is 0.0609/0.0648/0.3689. Higher FEM budgets cannot be presented as public-corpus evidence. The curves retain simple controls and do not assume that full fusion must be selected for deployment.

### 6.2 Threshold attainment and characterization work

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


The table retains non-attainment, and its conditional median is not a common-population saving estimate. Paired minimum-budget/cost comparisons preserve both-reached, one-sided and neither-reached outcomes. A favorable comparison to an anchor does not establish a benefit over adapted MLP or binary residual completion. Public savings refer only to simulated observations. FEM CPU numbers are recorded-cost replay; source pretraining and adaptation prevent converting them into a single measured end-to-end acceleration factor.

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


Original fine/validated CPU seconds and new completion wall seconds are different measurements. They describe the target-phase tradeoff without asserting an amortized or measured end-to-end acceleration.

### 6.3 Same-budget adaptation and related-work control

reference: at the frozen per-table threshold 0.28821552937419825, all 48 table/seed trajectories reach the threshold for both full and anchor. Their summed replayed fine-only CPU work is 1367.89 versus 3567.81 seconds. Full and adapted MLP instead require identical measured budgets in all 48 trajectories, with identical recorded characterization work. These sums count repeated experimental trajectories; they are not a unique PDK build cost.

to_asap7: at the frozen per-table threshold 0.2907519133283675, all 24 table/seed trajectories reach the threshold for both full and anchor. Their summed replayed fine-only CPU work is 765.41 versus 2005.59 seconds. Full and adapted MLP instead require identical measured budgets in all 24 trajectories, with identical recorded characterization work. These sums count repeated experimental trajectories; they are not a unique PDK build cost.

| Setting | B | Adapted AttentionCap | Adapted MLP | Full |
| --- | --- | --- | --- | --- |
| reference | 4 | 0.4546 | 0.0515 | 0.1233 |
| reference | 8 | 0.2256 | 0.0420 | 0.0925 |
| reference | 16 | 0.2025 | 0.0316 | 0.0409 |
| reference | 32 | 0.1677 | 0.0252 | 0.0332 |
| reference | 64 | 0.1657 | 0.0248 | 0.0250 |
| to_asap7 | 4 | 6.8753 | 0.0477 | 0.1182 |
| to_asap7 | 8 | 0.3199 | 0.0366 | 0.1034 |
| to_asap7 | 16 | 0.2120 | 0.0310 | 0.0685 |
| to_asap7 | 32 | 0.2153 | 0.0272 | 0.0495 |
| to_asap7 | 64 | 0.1791 | 0.0264 | 0.0386 |


The component-supervised official AttentionCap adaptation does not remove the stronger direct-MLP counterexample. Its finite training and modified heterogeneous-material/boundary representation limit conclusions about the original paper's method; no cross-paper benchmark ranking is made. The additional ASAP7-to-FreePDK15 direct-MLP experiment uses 8 fitting, 12 source-selection and 8 target-confirmation tables. Its pooled zero-target and adapted errors are 0.4414 and 0.0408, respectively. This is reverse-direction evidence for the direct baseline, not evidence that the full gate transfers bidirectionally. Two stacks still do not establish broad process generalization.

### 6.4 Native extraction and STA

| Layout | B | CMI net NRMSE | Full net NRMSE | CMI WS abs ns | Full WS abs ns | Full slack P99 ns | Full TNS abs ns |
| --- | --- | --- | --- | --- | --- | --- | --- |
| asap7/aes | 4 | 0.02499 | 0.00470 | 0.000597198 | 6.18024e-05 | 0.000297509 | 0.000618302 |
| asap7/aes | 8 | 0.02087 | 0.00228 | 0.00035999 | 4.17444e-05 | 0.000154629 | 0.00033303 |
| asap7/ibex | 4 | 0.02433 | 0.00452 | 0.00431977 | 0.000418739 | 0.000744047 | 0.00249834 |
| asap7/ibex | 8 | 0.02146 | 0.00232 | 0.00386909 | 6.76866e-05 | 0.00032921 | 0.000378549 |
| gf180/aes | 4 | 0.02269 | 0.00350 | 0.0197341 | 0.00296688 | 0.00393743 | 0.603678 |
| gf180/aes | 8 | 0.01824 | 0.00389 | 0.0158036 | 0.00339111 | 0.0042893 | 0.68748 |
| gf180/ibex | 4 | 0.01989 | 0.00308 | 0.0466828 | 0.00693401 | 0.00942794 | 10.1326 |
| gf180/ibex | 8 | 0.01613 | 0.00348 | 0.0382509 | 0.00814486 | 0.0109434 | 11.7671 |
| ihp-sg13g2/aes | 4 | 0.03268 | 0.00283 | 0.0380929 | 0.00208175 | 0.00351957 | 0 |
| ihp-sg13g2/aes | 8 | 0.02438 | 0.00306 | 0.0304389 | 0.00301093 | 0.00405604 | 0 |
| ihp-sg13g2/ibex | 4 | 0.03119 | 0.00233 | 0.0821106 | 0.00548687 | 0.00857911 | 0 |
| ihp-sg13g2/ibex | 8 | 0.02320 | 0.00289 | 0.0614021 | 0.00726056 | 0.0109562 | 0 |
| sky130hs/aes | 4 | 0.02542 | 0.00261 | 0.0187646 | 0.00102873 | 0.00254164 | 0.0022636 |
| sky130hs/aes | 8 | 0.00552 | 0.00070 | 0.00252516 | 0.000415593 | 0.000713067 | 0.00120815 |
| sky130hs/ibex | 4 | 0.02425 | 0.00281 | 0.0217722 | 0.00193801 | 0.00498963 | 0.591602 |
| sky130hs/ibex | 8 | 0.00458 | 0.00066 | 0.0024724 | 0.000544757 | 0.00108936 | 0.118745 |


All eight full-rule golden replays match archived net C and R exactly. All 240 planned budget/method/data-seed native evaluations complete with the same net and endpoint sets and unchanged R. The table reports seed means and absolute native deviations. Full improves net-C fidelity over CMI in 16/16 and absolute WS deviation in 16/16 case/budget cells; versus binary, the corresponding counts are 6/16 and 4/16. These descriptive cells share rule libraries and layouts and are not independent process samples. P99 slack, TNS, endpoint/path overlap, ranking and violation FN/FP are in the raw tables; no constraints were changed to create a favorable result. Full-rule reference agreement does not measure real-chip improvement.

### 6.5 Mechanism, failures and prior evidence

Full-versus-residual/binary comparisons and paired group intervals vary with setting and budget. Soft gate visualizations do not prove necessity or calibrated confidence. The registered pruning mask is an ablation and was not selected by source validation. No new acquisition network was built; random/coverage/curvature raw curves are retained. They change only the purchased support under a shared query and cost protocol.

For example, the public full-minus-binary NRMSE difference at B4 is -0.00851 with a pointwise 95% paired group interval [-0.01610, -0.0000880]. At B8 it is -0.00389 with interval [-0.01105, 0.000891], which includes zero. These comparisons quantify a conditional effect; they do not establish universal gate necessity, especially when most native cells favor binary. All 94 registered paired intervals are retained, along with three-training-seed ranges at fixed data seed 11; no favorable seed is selected.

Previously reported 30%-random-missing out-of-support cases remain counterexamples: FEM anchor/local-affine/full NRMSE is 0.0606/0.0621/0.0895; transfer is 0.0595/0.0594/0.0877. These are historical fixed-mask results, not new B-budget measurements. The previous public pruning speedup is also not generalized to rank-two or current low-budget inference. One new public execution attempt stalled in a forked worker, used 770.07 CPU seconds and emitted no records; its diagnostics and exact executed source are retained. Direct execution repaired orchestration without changing models or the frozen protocol. A native scheduler handoff preserved the running OpenROAD child and all outputs. Neither administrative event is hidden as successful scientific evidence.

## 7. Limitations and conclusion

The public geometry is rank one, FEM physics is idealized two-dimensional electrostatics, transfer covers only two stacks, and the available confirmation cohorts are not freshly blinded. The strongest new direct baseline uses finite source-validation tuning rather than exhaustive architecture optimization. The adapted AttentionCap feature and supervision interface differ from its original benchmark. No numerical Flash-CNNCap comparison is appropriate without a common three-dimensional window task. Historical source-generation/training CPU/GPU totals and true sparse-versus-full solver wall measurements are incomplete. Thresholds were validation-derived and are not certified downstream application requirements.

Support-conditioned completion is a useful offline rule-library interface and can improve fidelity at fixed target observation budgets. However, same-budget target adaptation and simple gates explain important benefits, and full fusion is not uniformly the efficient choice. We therefore retain the conservative rule-completion title and stop with COMPLETION_ACCURACY_ONLY. The evidence does not support the broader characterization-efficiency repositioning or justify an immediate submission on that claim. Further work would require a separately registered application threshold, stronger independent physical/deployment evidence and a clearly isolated contribution; it is not automatically launched in this study.

## References

[1] Huang et al. AttentionCap: Transformer Based Capacitance Matrix Learning Toward Full-Chip Extraction. DAC 2026 / arXiv:2606.08161. https://github.com/THU-numbda/AttentionCap

[2] Flash-CNNCap: Capacitance Extraction via Image Mapping. Official implementation, 2026. https://github.com/THU-numbda/flash-cnncap

[3] C.-Y. Tsai, S. Kim and S.-K. Lim. Capacitance Extraction via Machine Learning with Application to Interconnect Geometry Exploration. ICCAD 2025. doi:10.1109/ICCAD66269.2025.11240935.

[4] J.-C. Tsai et al. ResCap: Fast-yet-Accurate Capacitance Extraction for Standard Cell Design by Physics-Guided Machine Learning. ASP-DAC 2025. doi:10.1145/3658617.3697737.

[5] M. S. Abouelyazid, S. Hammouda and Y. Ismail. Accuracy-Based Hybrid Parasitic Capacitance Extraction Using Rule-Based, Neural-Networks, and Field-Solver Methods. IEEE TCAD 41(12), 5681–5694, 2022. doi:10.1109/TCAD.2022.3161199. Author institutional abstract: https://fount.aucegypt.edu/faculty_journal_articles/4632/

[6] M. Garnelo et al. Conditional Neural Processes. ICML 2018. https://proceedings.mlr.press/v80/garnelo18a.html

[7] H. Kim et al. Attentive Neural Processes. ICLR 2019 / arXiv:1901.05761. https://arxiv.org/abs/1901.05761

[8] AIL-DNN: Modeling of IC Interconnect Parasitic Capacitances Based on Adaptive Incremental Learning. IEEE TCAD, 2025. doi:10.1109/TCAD.2025.3562947. Detailed full-text methodological claims were not independently reverified in this run.


## Support-count mismatch and unresolved mechanism

Training-support mismatch remains an unresolved explanation rather than an established source of the observed performance differences.

The FEM models were trained on 153-node tables with 46, 77, 107 or 138 observed nodes under the missing-point protocols, or 136 under whole-width holdout. Thus the four low-budget evaluation conditions lie below the original support-count range. A paired continuation could distinguish extra optimization from a change in support protocol by holding the loss queries and family weights fixed while thinning the original supports. Such thinning also changes coverage, so it would not isolate cardinality alone.

A bounded attempt to construct this matched continuation stopped during preflight after exhausting its single permitted implementation repair. No continuation endpoint or matched endpoint evaluation was completed. The failure concerned the new audit harness, including comparison of unavailable analytic-basis entries represented by NaN, and provides no evidence for or against a low-support training effect. We therefore retain the existing completion-accuracy-only conclusion and make no new claim about architectural necessity, characterization efficiency, transfer, or downstream timing fidelity.
