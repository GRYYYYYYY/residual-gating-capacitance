# STA visualization: gf180 / ibex / block 50%

Real fixed-layout replay of the paper_v4 Table 22 audit; no training, rerouting, or ECO.

Spatial figures use seed 0, fixed before examining endpoint results. All three seeds are reported below.
The common final ODB, original SDC, Liberty, executable and input SPEFs are hashed in provenance.json.
All source audit ODB/SDC hashes agree. Resistance NRMSE is exactly zero for all selected exports.
Global WS/TNS reproduce archived values to their original rounding precision.

## Population and definitions

OpenSTA reports 3859 endpoints: 2039 constrained, 1820 unconstrained in every variant, zero missing. Unconstrained endpoints are retained with Inf in the raw/combined CSV and excluded explicitly from timing metrics. All 2039 constrained endpoints have real ODB coordinates. Internal pins use instance centers; output ports use physical pin-box centers.

Slacks and errors are in ns; coordinates are µm. Endpoint slack is the minimum setup slack across paths. Exported property values have 1e-6 ns display resolution. An absolute 2e-6 ns tolerance is used only to categorize gain ties; violation labels use the unshifted zero-slack threshold. No SDC or clock changes are introduced.

EP@K compares unique endpoints; start-end overlap compares pin pairs; full-path overlap compares the full ordered data-pin sequence. One worst path per endpoint is used, sorted by slack, endpoint and startpoint; K=10,20,50,100. Rank correlations cover all constrained endpoints. A polyline follows cell centers, not the metal routing.

Heatmaps use identical 50×50 bins and extent. Linear/ours share a zero-based color scale with no clipping. Empty bins are gray, not zero. Gain uses a symmetric diverging scale (blue positive, red negative). Additional scatter and bin-maximum maps are provided.

## Endpoint metrics (all seeds)

| seed | method | endpoints | mae_ns | rmse_ns | max_error_ns | slack_sign_accuracy | sign_mismatch_rate | precision | recall | f1 | spearman_rho | kendall_tau | TP | TN | FP | FN |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | linear | 2039 | 0.00587319 | 0.00611101 | 0.011923 | 0.99951 | 0.000490436 | 0.999455 | 1 | 0.999727 | 0.99999 | 0.998524 | 1833 | 205 | 1 | 0 |
| 0 | ours | 2039 | 0.00263433 | 0.00278994 | 0.004824 | 1 | 0 | 1 | 1 | 1 | 0.999996 | 0.999137 | 1833 | 206 | 0 | 0 |
| 1 | linear | 2039 | 0.0878745 | 0.0935214 | 0.17108 | 0.997548 | 0.00245218 | 1 | 0.997272 | 0.998634 | 0.997325 | 0.96858 | 1828 | 206 | 0 | 5 |
| 1 | ours | 2039 | 0.0261013 | 0.0276543 | 0.047792 | 0.999019 | 0.000980873 | 0.99891 | 1 | 0.999455 | 0.999603 | 0.989133 | 1833 | 204 | 2 | 0 |
| 2 | linear | 2039 | 0.0038416 | 0.00443246 | 0.018037 | 1 | 0 | 1 | 1 | 1 | 0.999843 | 0.994634 | 1833 | 206 | 0 | 0 |
| 2 | ours | 2039 | 0.00396151 | 0.00416374 | 0.007027 | 1 | 0 | 1 | 1 | 1 | 0.999994 | 0.998887 | 1833 | 206 | 0 | 0 |

## Critical endpoint / path overlap

| seed | method | K | endpoint_overlap | start_end_overlap | full_path_overlap |
| --- | --- | --- | --- | --- | --- |
| 0 | linear | 10 | 1 | 1 | 1 |
| 0 | linear | 20 | 1 | 1 | 1 |
| 0 | linear | 50 | 1 | 1 | 1 |
| 0 | linear | 100 | 1 | 1 | 1 |
| 0 | ours | 10 | 1 | 1 | 1 |
| 0 | ours | 20 | 1 | 1 | 1 |
| 0 | ours | 50 | 1 | 1 | 1 |
| 0 | ours | 100 | 1 | 1 | 1 |
| 1 | linear | 10 | 0.9 | 0.9 | 0.9 |
| 1 | linear | 20 | 0.95 | 0.95 | 0.95 |
| 1 | linear | 50 | 0.98 | 0.76 | 0.76 |
| 1 | linear | 100 | 0.74 | 0.42 | 0.42 |
| 1 | ours | 10 | 1 | 1 | 1 |
| 1 | ours | 20 | 1 | 1 | 1 |
| 1 | ours | 50 | 1 | 1 | 1 |
| 1 | ours | 100 | 0.98 | 0.98 | 0.98 |
| 2 | linear | 10 | 1 | 1 | 1 |
| 2 | linear | 20 | 1 | 1 | 1 |
| 2 | linear | 50 | 1 | 1 | 1 |
| 2 | linear | 100 | 1 | 1 | 1 |
| 2 | ours | 10 | 1 | 1 | 1 |
| 2 | ours | 20 | 1 | 1 | 1 |
| 2 | ours | 50 | 1 | 1 | 1 |
| 2 | ours | 100 | 1 | 1 | 1 |

## Gain statistics

| seed | fraction_ours_better | fraction_linear_better | fraction_tied | tie_tolerance_ns | mean_gain_ns | median_gain_ns | p90_gain_ns | max_gain_ns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.999019 | 0.000980873 | 0 | 2e-06 | 0.00323886 | 0.003324 | 0.0045502 | 0.00722 |
| 1 | 1 | 0 | 0 | 2e-06 | 0.0617732 | 0.060686 | 0.0939058 | 0.123915 |
| 2 | 0.511035 | 0.488475 | 0.000490436 | 2e-06 | -0.000119911 | 5.5e-05 | 0.0024878 | 0.011311 |

## Table 22 reproduction

| method | cap_nrmse_mean | max_abs_ws_ns | max_abs_tns_ns |
| --- | --- | --- | --- |
| linear | 0.0198619 | 0.13278 | 168.58 |
| ours | 0.00608173 | 0.03701 | 50.22 |

## Interpretation

Results describe agreement with golden extraction on a fixed routed layout, not timing closure, chip frequency, or signoff accuracy. Endpoint-error, rank and classification claims must be evaluated separately; a reduction in aggregate error does not imply every endpoint or every Top-K set improves.
