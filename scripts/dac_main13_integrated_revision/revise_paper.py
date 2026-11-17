"""First evidence-backed revision, applied once to the snapshotted main13 source."""
from pathlib import Path
R=Path(__file__).resolve().parents[2];p=R/'paper/dac_layout_query_revision/main.tex';s=p.read_text()
def replace(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
replace('Binary and Ungated are matched ablation controls used to assess the contribution of gated residual fusion.', 'We retain Full as the unified default for the consistency of these improvements across the evaluated domains and support conditions. Ungated and Binary improve over both baselines in 50 and 55 conditions, respectively; they can nevertheless have lower error than Full locally. This is a post-hoc empirical choice, not a guarantee for arbitrary unseen applications.')
replace('Full improves native net-capacitance','Full improves rule-export net-capacitance')
replace('Instead, our comparison focuses on fast parasitic extraction approaches based on pattern matching and lookup-table interpolation, represented by the open-source OpenRCX \\cite{openroad_openrcx} and the commercial Calibre xRC \\cite{siemens_calibre_xrc}.','Our controlled algorithmic comparison uses OpenRCX \\cite{openroad_openrcx} and a specified generic numerical interpolation baseline with identical observable support. Commercial product-level comparisons would require matched characterization inputs and access to equivalent evaluation interfaces.')
replace('Specified MLI implements the mathematical core of supplied Calibre xRC fast interpolation.','MLI is a generic tensor interpolation baseline; we do not establish equivalence to a proprietary Calibre xRC kernel.')
replace('using $\\mathbf{s}_y$.\n\n\n\\subsection{Native Compute-Table Population}',r'''using $\mathbf{s}_y$.

Ungated uses $[b+r_{\rm NN}]_+$ and Binary uses
$[b+\alpha r_{\rm NN}]_+$ with component-wise $0\leq\alpha\leq1$.
Binary retains support descriptors but removes numerical corrections,
NN-Clip, and agreement features. These separately trained models have their
own neural parameters, so their differences do not isolate a single gate
coefficient. Full's weights normalize over valid candidates, but candidate
validity is not accuracy; agreement is neither calibrated uncertainty nor
a no-regression certificate.

\subsection{Native Compute-Table Population}''')
replace('The original\ncharacterization support is retained throughout\npreparation; generated values are never reused\nas observations.',r'''The available characterization support $S$ is retained throughout
preparation; generated values are never reused as observations.
For sparse-native evaluation, hidden rows are physically removed before
the native constructor runs. The original full-support experiment is
reported separately. Native-sparse and all three injection arms share
the same sparse rules and resulting canonical grid; unsupported rules
remain identical across arms. Hidden capacitances therefore cannot return
through the native getter or its boundary fallback.''')
replace(r'$\mathcal{T}\leftarrow\mathcal{C}(\mathcal{R})$\;',r'''$\mathcal{R}_S\leftarrow\operatorname{RetainAvailableSamples}(\mathcal{R},\mathcal{S})$\;
$\mathcal{T}\leftarrow\mathcal{C}(\mathcal{R}_S)$\;''')
replace('requiring at least four matched real samples,','requiring at least four original candidate samples, using the available capped budget,')
replace('Learned completion predictions average three trained members.',r'''Learned completion predictions average three trained members.
The public fit/select/confirm counts describe deduplicated tables rather
than an additive partition of the raw inventory; native holdout is a
separately reserved subset. Confirmation scores reused for the present
default-selection and mechanism analysis are post-hoc evidence.

Full/Binary/Ungated optimize source-scaled component Huber loss
($\delta=1$), with one sampled episode per family per update, uniform
family weights, AdamW learning rate $2\times10^{-4}$ and weight decay
$10^{-4}$. The frozen recipe uses gradient clipping at 1, no dropout,
two Transformer layers of width 64, four heads, and gate hidden width 32.
Source residual initialization and source-fitted scales are reused;
the final prescribed step is retained. MLP/CNP use 3k updates, three
members and source selection over learning rates $10^{-3}$ and
$3\times10^{-4}$; MLP adaptation is selected from 0/50/200 steps.
Adapted AttentionCap uses 3k updates with batches of up to 32 geometries,
three members and the same learning-rate/adaptation grid. Its supervision
is the three task components, not complete capacitance matrices. These
are documented, unequal training opportunities; identical $B$ matches
target observations, not total source training or tuning cost.''')
replace('Coverage scores average process/family/component groups and then masks;',r'''Coverage scores average process/family/component groups and then masks;
paired uncertainty resamples public split groups or FEM/transfer
process--layer groups, keeping correlated queries and masks together.
The 60 condition counts are descriptive, not 60 independent tests.
FEM/transfer have only four/two layer groups, limiting interval interpretation;''')
replace('\\input{tables/coverage_findings.tex}',r'''\input{tables/coverage_findings.tex}

\begin{table}[t]
\centering\small\setlength{\tabcolsep}{3pt}
\caption{Baseline-improvement consistency over all 60 conditions.
Strict wins use unrounded errors; $R=E/\min(E_{\rm ORCX},E_{\rm MLI})$
and $G=1-R$. The stronger baseline is an analysis reference, not a
deployable oracle. Float32-scale tolerance yields the same three-variant counts.}
\label{tab:consistency}
\input{tables/baseline_consistency.tex}
\end{table}

Full is the only one of these three matched variants whose condition-level
point estimates improve over both kernel baselines in every tested cell
(Table~\ref{tab:consistency}). This motivates its unified default status,
rather than requiring it to minimize every metric. Its narrowest margin
is Transfer In/block at 10\% holdout: 0.064318 versus the stronger baseline
0.067879, a 5.25\% reduction. The paired error-difference interval is
$[-0.01098,0.00534]$ under a 1,000-replicate layer-group bootstrap;
with only two independent layer groups, this is descriptive uncertainty,
not evidence that regression risk has been eliminated.

Ungated's largest regression is Transfer In/random at 50\% holdout
(0.068591 versus 0.038578); Binary also regresses there (0.052029).
Both additionally regress on FEM and Transfer In/block at 10\% holdout.
These cases are consistent with inaccurate residual corrections when the
support-derived baseline is already accurate, but separately trained
residuals prevent a causal attribution to suppression alone. Conversely,
simple corrections can be more accurate when additional fusion is
unhelpful. All successes and regressions remain in the evaluation.''')
replace('At $B=4/8$, Full reduces net-capacitance','In the fixed-node rule-export protocol at $B=4/8$, Full reduces net-capacitance')
replace('New computeTable path, Full:','Full-characterization compute-table path, Full:')
replace('The compute-table path keeps mean extraction time within 3.5\\% of native extraction,','The separate full-characterization compute-table path keeps mean extraction time within 3.6\\% of native extraction,')
replace('Global attention makes predictions depend on Q.', 'Global attention makes predictions depend on Q; deterministic sorting does not imply query-set invariance.')
replace('Full thus targets prediction under limited characterization,','Full remains the default for empirical cross-condition improvements over the two specified kernel baselines, while Binary/Ungated local optima and stronger numerical controls delimit its scope. Full thus targets prediction under limited characterization,')
p.write_text(s)
