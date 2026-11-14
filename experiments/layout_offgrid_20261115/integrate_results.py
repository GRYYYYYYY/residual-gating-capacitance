import json
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/layout_offgrid_20261115';P=R/'paper/dac_layout_query_revision'
a=json.loads((O/'metric_summary.json').read_text());lookup={(r['reference_kind'],r['method'],r['weighting']):r['macro_nrmse'] for r in a}
methods=[('cmi','Multilinear'),('anchor','Support anchor'),('affine','Local affine'),('gp','RBF-GP'),('residual','Ungated'),('binary','Binary'),('full','Full'),('mlp_adapt','Adapted MLP'),('cnp','CNP')]
lines=[r'\begin{tabular}{lrrr}\toprule',r'Method & Native agreement & FEM unique & FEM weighted\\\midrule']
for m,label in methods:
 vals=[lookup['native_evaluator_agreement_not_physical_truth',m,'unique'],lookup['direct_FEM_template_F_per_m',m,'unique'],lookup['direct_FEM_template_F_per_m',m,'occurrence_HT']]
 lines.append(label+' & '+' & '.join(f'{v:.5f}' for v in vals)+r'\\')
lines+=[r'\bottomrule\end{tabular}'];(P/'tables/offgrid.tex').write_text('\n'.join(lines))
section=r'''
\subsection{Native queries and independent template references}
We instrument two capacitance getters in OpenROAD
\texttt{0b54bb3203}: finite width/distance evaluation and indexed fringe lookup.
Original and instrumented extraction produce identical SPEF electrical records
on all eight fixed routed databases. Across 9,888,586 logged calls and 19,562
unique rule/geometry keys, 2,696,515 calls hit characterization nodes,
4,547,424 are non-node queries within the selected width slice's support,
and 967,755 lie outside it. The remaining 1,676,892 are fringe/special calls.
Non-node calls represent 55.77\% of this denominator and 67.16\% of finite
distance calls. The trace excludes resistance, five-argument diagonal getters,
and subsequent assembly; it is not a count of every extraction operation.

\begin{figure*}[t]
\centering\includegraphics[width=\textwidth]{figures/query_census.pdf}
\caption{Measured query distribution on eight unchanged layouts. Left: occurrence-weighted classes over the two logged getters. Right: native M4 width/spacing requests from ASAP7 and original rule knots; marker area reflects log occurrence. Classification uses integer database coordinates and the selected native width slice.}
\label{fig:census}
\end{figure*}

OpenRCX maps widths and constructs an internal distance compute grid.
Among raw non-node calls, 849,663 return an effective characterization node;
these are reported as quantized-to-node, separately from interpolation.
An independent reproduction of the finite, non-sentinel computation matches
29,735 design-specific query records (8,211,694 occurrences), with maximum
support-scaled difference $2.1\times10^{-16}$. Rule identity is uniquely
resolved for 95.42\% of logged calls. This is an interface identity result;
matching rule names does not establish matching electrostatic materials.

\begin{table}[t]
\centering\caption{Off-grid query comparisons, macro NRMSE. Native agreement: 480 queries from 42 source-held-out rule groups, using every supplied rule sample and actual OpenRCX returns as reference. FEM: 71 independent template queries with 153 matched support samples per context. Weighted FEM uses occurrence counts divided by sampling probability. Native agreement and direct physical error have different references and units; compare methods only within a column.}
\label{tab:offgrid}\scriptsize\setlength{\tabcolsep}{2pt}\input{tables/offgrid.tex}
\end{table}

For direct reference evaluation, 114 geometry candidates arise from ASAP7 AES
and Ibex calls on M4/M5 with adjacent OVER, UNDER, and OVERUNDER contexts.
They account for 86,587 calls (0.876\% of the logged denominator).
Geometry-only, hash-ordered stratification fixes 12 pilot and 71 formal queries
before solving or inspecting errors. Each query is absent from the original
CTF characterization nodes at database resolution. Widths are 0.024 or
0.032\,$\mu$m. All 153 original samples in each of six contexts remain available;
no characterization node is masked to create these queries.

The physical cohort is a \emph{layout-parameterized template}: logged width
and spacing drive symmetric, equal-width side wires, finite adjacent grounded
planes, and an exterior grounded boundary in the declared ASAP7 CTF stack.
It does not retain arbitrary asymmetric routing, net connections, or a full
layout section. Ground and summed lateral coupling are projected from the
Maxwell matrix in F/m. Original native calibration materials and projections
are not jointly aligned with this template, so no native-versus-FEM physical
accuracy claim is made. For the same template, direct P2 FEM solves provide
query labels independently of prediction; support geometry, solver hashes,
and component projections are verified against the reused matrices.

All 83 pilot/formal geometries pass coarse/fine/doubled-domain checks and
component-scaled convergence limits. Twelve additional on-grid controls
reproduce the reused matrices exactly. Macro normalized component uncertainty
is 0.00016, compared with Anchor/Full/Binary errors of
0.00451/0.01675/0.02218. Source training and selection for this cohort use
FreePDK15 only. Table~\ref{tab:offgrid} shows that the support anchor is more
accurate than learned correction with the full supplied characterization.
Full improves over Binary and adapted MLP on this cohort, but does not improve
on numerical interpolation. In native replay, interpolation also agrees more
closely with OpenRCX than the learned methods. Agreement alone does not rank
physical accuracy.

Queries are sorted by geometry hash within a rule context and processed in
chunks of at most 32 with all support samples. Original-grid API outputs and
support restoration are bit-exact. Development checks show that changing
query sets changes Full's predictions (maximum 0.0205 in source-normalized
units in the public check), while fixed-policy input reordering leaves them
unchanged. This is batch-conditioned query evaluation. Mean three-member
FEM-batch wall times, including encoding and numerical branches, are
43.67\,ms for Full, 25.33\,ms for Binary, and 8.32\,ms for Anchor;
MLP fitting plus prediction takes 605.07\,ms. Model loading and reference
solving are separate costs. These measurements do not establish end-to-end
PEX speedup or online replacement.

'''
s=(P/'main.tex').read_text();marker='\\subsection{Native queries and independent template references}'
if marker not in s:s=s.replace('\\subsection{Discussion}',section+'\\subsection{Discussion}')
s=s.replace('Experiments cover public rules, finite-element references, cross-process prediction, and native extraction.','Experiments cover controlled characterization subsampling, finite-element references, cross-process prediction, and native extraction.')
s=s.replace('Fixed-budget comparisons and matched controls characterize accuracy and computation tradeoffs among full fusion, binary gating, and target-adapted prediction under shared target observations.','A native census records 9.89 million calls. On 71 layout-parameterized off-grid templates with full support, numerical interpolation outperforms the learned corrections, identifying a limit to gains from controlled subsampling.')
s=s.replace('Our contributions are:',r'We also measure native query occurrence and evaluate a declared physical template at genuinely new layout-derived coordinates, separating native agreement from independent field-reference error. Our contributions are:')
s=s.replace('their fixed-missingness counterparts and native MLP/GP comparisons remain unevaluated.','their controlled-subsampling counterparts use distinct protocols.')
s=s.replace('their controlled-subsampling counterparts and native MLP/GP comparisons remain unevaluated.','their controlled-subsampling counterparts use distinct protocols.')
s=s.replace('The applicable support protocol is therefore central to choosing predictor complexity.','With all supplied characterization samples, interpolation is more accurate on the layout-parameterized template cohort. Query-level replay, offline addition of rule nodes, and in-extractor replacement are distinct deployment levels. The evidence here supports replay and fixed-grid rule export; node enrichment and online model substitution are not established.')
s=s.replace('The interface combines learned cross-table information with observations already available in a rule library.','The native census establishes the occurrence of non-node requests, while direct template references show that learned corrections need not improve interpolation when the full characterization support is available. Support conditions and physical interface coverage determine the useful scope of conditional estimation.')
(P/'main.tex').write_text(s)
# Preserve a complete editable treatment before publication-length condensation.
(P/'extended.tex').write_text(s.replace('\\clearpage\n\\bibliographystyle',r'''\begin{figure*}[t]
\centering\includegraphics[width=\textwidth]{figures/query_errors.pdf}
\caption{Occurrence and error versus S-only normalized nearest-support distance. Fixed bins are shared by all methods; the direct reference is the declared template, not an exact layout section. Occurrence estimates use inverse inclusion probabilities.}
\end{figure*}
\clearpage
\bibliographystyle'''))
