from pathlib import Path
P=Path(__file__).resolve().parents[2]/'paper/dac_layout_query_revision'
s=(P/'main.tex').read_text()
a=s.index('\\subsection{Support-protocol sensitivity and computational tradeoffs}');b=s.index('\\subsection{Native queries and independent template references}',a)
s=s[:a]+r'''\subsection{Support-protocol sensitivity}
Matched 2,000-step continuation compares original-support (H) and low-budget
coverage sampling (L) for Full/Binary, with three seeds. The H-minus-L mean
error improvement is 0.005066 for Full and 0.015766 for Binary. Binary-L wins
at $B=4$ for all seeds and at $B=8$ for two; Full-L wins at $B=16,32$ but is
20.0\%/28.9\% less accurate than source-trained Full. Original-support retention
error increases from 0.04359 to 0.05209 for Full-L. Thus sparse-support
continuation narrows Full's average advantage over Binary from 0.014088 to
0.002939, with a denser-support accuracy cost. These mean-member,
group-balanced scores use a different aggregation from the ensemble budget
comparison; the expanded analysis retains per-seed curves and component tails.

'''+s[b:]
# Retain native tail findings while eliminating repeated averages.
a=s.index('Equal-layout averages also favor Binary');b=s.index('Tail and decision metrics',a)
s=s[:a]+s[b:]
# The expanded editable treatment retains all detailed source evidence.
s=s.replace('\\label{tab:offgrid}\\scriptsize','\\label{tab:offgrid}\\small')
# A concise introduction with all source-supported facts and unchanged results.
a=s.index('We evaluate the estimator using controlled characterization subsampling,');b=s.index('Our contributions are:',a)
s=s[:a]+r'''We evaluate controlled characterization subsampling, support-size sensitivity,
cross-process prediction, and native extraction fidelity. Full improves over
Binary in all five FEM conditions at 30\% holdout, whereas sparse-support
comparisons and downstream tails often favor simpler methods. A native query
census and direct reference solves on declared layout-parameterized templates
then test relevance and accuracy when all supplied samples remain available.
These evaluations separate native agreement from physical reference error.

'''+s[b:]
(P/'main.tex').write_text(s)
