"""Join the two archived display tables without changing their metric values."""
from pathlib import Path
import json,re,hashlib
P=Path(__file__).resolve().parent
sources=['tables/downstream_two_kernels.tex','tables/compute_deployment.tex']
def read_rows(name):
 out=[]
 for line in (P/name).read_text().splitlines():
  if '&' in line and line.split('&')[0].strip().lower().startswith(('asap7/','gf180/','ihp/','sky')):
   out.append([x.strip() for x in line.removesuffix('\\\\').split('&')])
 return out
def key(name):
 process,design=name.lower().split('/');return ('sky130' if process=='sky' else process,design)
a=read_rows(sources[0]);b={key(r[0]):r for r in read_rows(sources[1])};assert len(a)==len(b)==8
lines=[r'\begingroup',r'\fontsize{5.8}{6.5}\selectfont',r'\setlength{\tabcolsep}{0.75pt}\setlength{\arrayrulewidth}{0.25pt}',r'\renewcommand{\arraystretch}{1.0}',r'\newcommand{\layoutspan}[1]{\raisebox{-3.25pt}[0pt][0pt]{#1}}',r'\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}|l|c||rrr|rrr||rrrrr|}',r'\hline',r'\multicolumn{2}{|c||}{\textbf{Layout / budget}} & \multicolumn{6}{c||}{\textbf{Rule-export: error reduction (\%)}} & \multicolumn{5}{c|}{\textbf{Full-support compute table}} \\',r'\cline{3-13}',r' & & \multicolumn{3}{c|}{vs. MLI-ext.} & \multicolumn{3}{c||}{vs. OpenRCX} & \multicolumn{5}{c|}{Fidelity and preparation / extraction cost} \\',r'\cline{3-13}',r'\textbf{Layout} & $B$ & C & WS & TNS & C & WS & TNS & C err. & Prep. & PEX & SPEF & $T/T_0$ \\',r'\hline']
joined=[]
for row in a:
 layout=row[0];native=b[key(layout)][1:];pairs=[x.split('/') for x in row[1:]];assert len(pairs)==6 and all(len(x)==2 for x in pairs)
 for i,budget in enumerate([4,8]):
  label=(r'\layoutspan{\textbf{'+layout+'}}') if i==0 else ''
  native_cells=[r'\layoutspan{'+v+'}' for v in native] if i==0 else ['']*5
  lines.append(' & '.join([label,str(budget)]+[x[i] for x in pairs]+native_cells)+r' \\')
 lines.append(r'\hline');joined.append(dict(layout=layout,rule_export_pairs=row[1:],native_values=native))
lines += [r'\end{tabular*}',r'\par\vspace{2pt}',r'\parbox{\columnwidth}{\fontsize{6}{6.7}\selectfont Rule-export values average seeds 11/29/47. C denotes capacitance NRMSE. WS/TNS are absolute timing deviations from full-table extraction. A dash denotes zero error for both methods. For internal deployment, C err. is net-C NRMSE. Prep./PEX/SPEF are in seconds. $T/T_0$ is the mean extraction ratio over three release runs. Preparation includes inventory and loading. Native table construction/injection stays within PEX. The right-hand values share full characterization across budgets.}',r'\endgroup']
(P/'tables/downstream_merged.tex').write_text('\n'.join(lines)+'\n')
(P/'TABLE_MERGE_VERIFICATION.json').write_text(json.dumps(dict(status='PASS',layouts=8,rule_export_budget_rows=16,rule_export_values=96,native_values=40,source_sha256={x:hashlib.sha256((P/x).read_bytes()).hexdigest() for x in sources},joined=joined,protocols_kept_distinct=True),indent=2))
print('MERGED_TABLE_PASS 8 layouts / 96 rule-export values / 40 native values')
