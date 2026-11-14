"""Generate TeX from the one authoritative Markdown source; no experimental work."""
import re,sys
from pathlib import Path
PAPER=Path(sys.argv[1]);body=(PAPER/'DAC_REWRITE.md').read_text()
def esc(s):
 urls=[]
 def protect(m):
  urls.append(m.group(0));return 'URLTOKEN'+str(len(urls)-1)+'END'
 s=re.sub(r'https?://[^\s]+',protect,s)
 s=s.replace('→',r'$\rightarrow$').replace('–','--').replace('—','---')
 for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:s=s.replace(a,b)
 s=re.sub(r'\*\*(.+?)\*\*',r'\\textbf{\1}',s)
 for j,url in enumerate(urls):s=s.replace('URLTOKEN'+str(j)+'END',r'\url{'+url+'}')
 return s
lines=body.splitlines();tex=[];i=1;table_number=0
captions=['Fixed-budget macro NRMSE; smaller is better. All methods share the same S and Q.', 'Attainment at the frozen middle threshold. Conditional medians must be read with censored counts.', 'Recorded characterization CPU work and measured completion wall time, reported separately.', 'Component-supervised adaptation of official AttentionCap, not its original benchmark.', 'Native extraction and STA fidelity against full-rule extraction; seed means.', 'Paired support-protocol effects for each source-training seed; table/group primary NRMSE.']
while i<len(lines):
 line=lines[i]
 if line.startswith('| '):
  block=[]
  while i<len(lines) and lines[i].startswith('| '):block.append([x.strip() for x in lines[i].strip('|').split('|')]);i+=1
  block=[b for b in block if not all(x=='---' for x in b)]
  cols=len(block[0]);tex.append(r'\begin{table*}[t]\centering\scriptsize\resizebox{\textwidth}{!}{\begin{tabular}{'+'l'*cols+'}'+r'\toprule')
  for j,b in enumerate(block):tex.append(' & '.join(esc(x) for x in b)+r'\\'+(r'\midrule' if j==0 else ''))
  tex.append(r'\bottomrule\end{tabular}}\caption{'+esc(captions[table_number])+r'}\end{table*}');table_number+=1;continue
 if line.startswith('### '):tex.append(r'\subsection{'+esc(re.sub(r'^\d+\.\d+\s*','',line[4:]))+'}')
 elif line.startswith('## '):
  title=re.sub(r'^\d+\.\s*','',line[3:]);tex.append(r'\section*{'+esc(title)+'}')
  if title=='Introduction':tex.append(r'\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{figures/workflow.pdf}\caption{Budgeted offline rule completion and fixed-layout extraction/STA fidelity.}\end{figure*}')
  if title=='Method and alternatives':tex.append(r'\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{figures/architecture.pdf}\caption{Support-derived anchor and jointly trained residual fusion. GP ridge values match executed code.}\end{figure*}')
  if title=='Matched support-protocol continuation':
   tex.append(r'\begin{figure*}[t]\centering\includegraphics[width=.48\textwidth]{figures/error_budget.pdf}\includegraphics[width=.48\textwidth]{figures/paired_effects.pdf}\caption{Matched source continuation: fixed-query low-budget errors and paired effects. Faint lines show all three training seeds; intervals condition on four existing dependency groups.}\end{figure*}')
  if title=='Results':
   for file,caption in [('budget_accuracy','Fixed-Q budget curves; public has no eligible table at B16 or above.'),('fixed_error_cost','Minimum measured work at the frozen middle threshold. Conditional medians and IQRs; labels retain attainment coverage.'),('completion_cost','Completion and target-adaptation wall cost versus error; characterization and historical source costs are separate.'),('gating_training_seeds','Full, residual and binary sensitivity across three source-training seeds at fixed data seed; bands are seed ranges, not confidence intervals.'),('native_fidelity_B4','Native net capacitance and worst-slack fidelity at B4. Lower deviation is better; constraints remain fixed.')]:
    tex.append(r'\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{figures/'+file+r'.pdf}\caption{'+esc(caption)+r'}\end{figure*}')
 else:tex.append(esc(line))
 i+=1
header=r'''\documentclass[10pt,twocolumn]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.7in]{geometry}
\usepackage{graphicx,booktabs,amsmath,url}
\usepackage[hidelinks]{hyperref}
\setlength{\emergencystretch}{3em}
\title{Support-Conditioned Completion of Capacitance Rules for Parasitic Extraction}
\author{Research revision}
\date{14 November 2026}
\begin{document}\maketitle
'''
(PAPER/'main.tex').write_text(header+'\n'.join(tex)+'\n\\end{document}\n')
