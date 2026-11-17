"""Data-driven prose for the completed bounded controls; no model selection."""
from pathlib import Path
import csv
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';P=R/'paper/dac_layout_query_revision'
rs={r['method']:r for r in csv.DictReader((O/'mechanism_summary.csv').open())};c1=rs['numerical_gate'];c2=rs['fixed_fusion'];c3=rs['no_agreement'];full=rs['full_replay']
text=f"Table~\\ref{{tab:mechanism_controls}} reports all 60 conditions. Numerical-only gating (C1) improves over both kernels in {c1['beats_both']}/60 cells under strict comparison ({c1['beats_both_tolerance']}/60 with the same numerical tolerance), with worst ratio {float(c1['worst_error_ratio']):.4f}; it is locally better than Full in {c1['beats_full']}/60. "
if int(c1['beats_both'])<60 and int(c1['beats_full'])<30:text+='This supports the combined neural representation/candidate pathway under this recipe, while preserving numerical-only local wins. C1 removes the Transformer state and both neural candidates together, so it does not isolate each element. '
else:text+='This result does not establish that every component of the neural pathway is necessary. '
text+=f"The frozen-candidate fixed mixture (C2) improves both kernels in {c2['beats_both']}/60 cells and has worst ratio {float(c2['worst_error_ratio']):.4f}, versus Full's {float(full['worst_error_ratio']):.4f}. This intervention supports adaptive weighting relative to the tested source-fitted mixture, not superiority over every possible fixed mixture or a retrained fixed-fusion architecture.\n\n"
text+=f"Removing agreement with matched retraining (C3) yields {c3['beats_both']}/60 strict improvements ({c3['beats_both_tolerance']}/60 with tolerance), worst ratio {float(c3['worst_error_ratio']):.4f}, and {c3['beats_full']}/60 local wins over Full. The unweighted means of condition errors are {float(c3['mean_cell_error']):.5f} for C3 and {float(full['mean_cell_error']):.5f} for Full. "
if int(c3['beats_both'])==60:text+="Agreement is therefore not necessary for the headline 60/60 point-estimate property in this recipe. The earlier uniqueness statement applies to Ungated/Binary/Full, not to every further control. We retain Full as the evaluated default but do not attribute its baseline-improvement coverage solely to agreement. "
else:text+="This provides conditional evidence for agreement in this training recipe, without establishing its necessity in other settings. "
text+='These source-trained interventions remain post-hoc analyses of correlated confirmation conditions, not independent evidence of a safety guarantee.\n'
(P/'tables/mechanism_control_findings.tex').write_text(text);print(text)
