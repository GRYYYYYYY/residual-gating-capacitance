from pathlib import Path
import re
R=Path(__file__).resolve().parents[2];P=R/'paper/dac_layout_query_revision'
s=(R/'paper/dac_submission_rewrite/main.tex').read_text()
s=s.replace('Observation-Conditioned Capacitance Rule Completion for Parasitic Extraction','Characterization-Conditioned Capacitance Estimation for Rule-Based Parasitic Extraction').replace('pdfsubject={Capacitance rule completion}','pdfsubject={Characterization-conditioned capacitance estimation}')
intro=(R/'docs/layout_offgrid_20261115/task_inputs/intro_motivation.tex').read_text()
intro='\n'.join(x for x in intro.splitlines() if not x.startswith('%'))
intro=intro.replace('tsai2025geometry','tsai').replace('orcx_calibration','openrcx')
a=s.index('Parasitic extraction supplies');b=s.index('Useful model complexity',a)
s=s[:a]+intro+'\n\n'+s[b:]
s=s.replace('We present observation-conditioned completion','We present characterization-conditioned estimation').replace('30\\% missingness','30\\% characterization holdout').replace('Observation-conditioned rule completion using target observations','Characterization-conditioned estimation using shared target samples').replace('Evaluation across missingness, observation budgets, and processes','Evaluation across characterization coverage, support sizes, and processes')
s=s.replace('\\subsection{Rule completion from available observations}','\\subsection{Pre-characterized rule evaluation}')
a=s.index('A table contains candidate');b=s.index('\\subsection{Relation to',a)
s=s[:a]+r'''For a fixed process, corner, pattern family, and context $c$, let
$S=\{(x_i,y_i)\}$ be the available characterization samples and let $Q$
contain query geometries. Only the values in $S$ enter prediction:
\begin{equation}
\widehat y_Q=F_\theta(S,Q,c),\qquad \widehat y(x_i)=y_i\quad(x_i\in S).
\label{eq:interface}
\end{equation}
An on-grid query coincides with a characterization node. An off-grid query
is in-support if it lies in the valid support hull, and out-of-support if
it lies outside that hull while retaining compatible geometry and output
semantics. Rank-deficient supports require membership in their affine
space; coordinate-wise bounds alone are insufficient. Unsupported material,
conductor topology, or component definitions are coverage exclusions.

Controlled characterization subsampling reserves reference nodes as queries;
a 30\% holdout supplies the remaining 70\% to every predictor. This protocol
measures support coverage sensitivity and does not measure the distribution
of runtime queries. Inference uses the union of support and query coordinates,
including query--query attention, so predictions are batch-conditioned.
The same conditioning interface applies to a new process with fixed $\theta$.

'''+s[b:]
s=s.replace('\\section{Observation-Conditioned Rule Completion}','\\section{Characterization-Conditioned Estimator}')
s=s.replace('\\emph{Fixed missingness}','\\emph{Controlled characterization subsampling}').replace('\\emph{Fixed observation budgets}','\\emph{Characterization-support-size sensitivity}')
s=s.replace('rank-matched commercial-style multilinear interpolation (CMI)','rank-matched multilinear interpolation (CMI)').replace('OpenRCX-style linear interpolation','piecewise-linear interpolation')
s=s.replace('\\subsection{Fixed-missingness completion and matched controls}','\\subsection{Controlled characterization subsampling}')
s=s.replace('Fixed-missingness completion at 30\\%','Controlled characterization subsampling at 30\\%')
s=s.replace('missingness ratios are','holdout ratios are').replace('block missingness','block holdout').replace('patterns of missing support','characterization coverage patterns').replace('at 50\\% missingness','at 50\\% holdout').replace('layout--missingness','layout--holdout')
s=s.replace('We presented observation-conditioned capacitance rule completion','We presented characterization-conditioned capacitance estimation')
s=s.replace('Several strong methods meet the evaluated source-validation tolerances at the first tested $B=4$, leaving lower necessary characterization budgets unresolved.','Several strong methods meet the evaluated source-validation tolerances at the first tested $B=4$. These minimum-budget results are retrospective comparisons, not deployment stopping rules with access to query truth.')
(P/'main.tex').write_text(s)
bib=(R/'paper/dac_submission_rewrite/references.bib').read_text()
new=(R/'docs/layout_offgrid_20261115/task_inputs/offgrid_references.bib').read_text()
for entry in re.split(r'\n(?=@)',new):
 if not any('{'+k+',' in entry for k in ['orcx_calibration','tsai2025geometry']):bib+='\n'+entry
(P/'references.bib').write_text(bib)
