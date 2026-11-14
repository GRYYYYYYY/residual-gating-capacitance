"""Render the sole Markdown primary source, without experimental imports."""
from pathlib import Path
import re
P=Path(__file__).resolve().parent
body=(P/'DAC_REWRITE.md').read_text()
def esc(s):
 urls=[]
 def protect(m):urls.append(m[0]);return 'URLTOKEN'+str(len(urls)-1)+'END'
 s=re.sub(r'https?://[^\s]+',protect,s)
 s=s.replace('→',r'$\rightarrow$').replace('–','--').replace('—','---').replace('−','-')
 for a,b in [('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:s=s.replace(a,b)
 s=re.sub(r'\*\*(.+?)\*\*',r'\\textbf{\1}',s)
 for j,u in enumerate(urls):s=s.replace('URLTOKEN'+str(j)+'END',r'\url{'+u+'}')
 return s
captions=['Historical E1 pooled query NRMSE, using archived three-member predictions for trained ensembles; same S/Q across methods.','Historical threshold attainment; conditional medians retain non-attainment.','Historical recorded characterization CPU and measured adaptation/completion wall costs, kept separate.','Adapted AttentionCap, MLP and Full under E1; three-member prediction aggregation, not mechanism M.','Mechanism M: means of three individual-member errors; original Full is retained.','Paired continuation effects in M units, separately for all three training seeds.','Original-support retention: M-style table/group aggregation, then three-member error means.','Single-member completion CPU estimates in ms: shared encoding plus one forward; not ensemble wall latency.','Archived native CMI, binary and Full. First average three data seeds per layout/budget, then eight layouts. Timing values in ps are reference errors; averaged per-run P99 is not a pooled percentile.']
lines=body.splitlines();out=[];i=1;n=0
while i<len(lines):
 line=lines[i]
 if line.startswith('| '):
  block=[]
  while i<len(lines) and lines[i].startswith('| '):block.append([x.strip() for x in lines[i].strip('|').split('|')]);i+=1
  block=[b for b in block if not all(x=='---' for x in b)]
  env='table' if n==8 else 'table*';width=r'\columnwidth' if n==8 else r'\textwidth'
  if n==8:block[0]=['B','Method','C NRMSE','WS err ps','P99 err ps']
  box=('\\resizebox{'+width+'}{!}') if n in [0,1,2,8] else ''
  out.append('\\begin{'+env+('}[!ht]' if n==8 else '}[t]')+'\\centering\\small'+box+'{\\begin{tabular}{'+'l'*len(block[0])+r'}\toprule')
  for j,b in enumerate(block):out.append(' & '.join(esc(x) for x in b)+r'\\'+(r'\midrule' if j==0 else ''))
  out.append(r'\bottomrule\end{tabular}}\caption{'+esc(captions[n])+'}\\end{'+env+'}');n+=1;continue
 if line.startswith('!['):
  m=re.fullmatch(r'!\[(.*)\]\((.*)\)',line);out.append(r'\begin{figure*}[t]\centering\includegraphics[width=.8\textwidth]{'+m[2]+r'}\caption{'+esc(m[1])+r'}\end{figure*}')
 elif line.startswith('### '):out.append(r'\subsection*{'+esc(line[4:])+'}')
 elif line.startswith('## '):
  if line=='## References':out.append(r'\clearpage')
  out.append(r'\section*{'+esc(line[3:])+'}')
 else:out.append(esc(line))
 i+=1
assert n==len(captions)
header=r'''\documentclass[10pt,twocolumn]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.7in]{geometry}
\usepackage{graphicx,booktabs,amsmath,url}
\usepackage[hidelinks]{hyperref}
\setlength{\emergencystretch}{3em}
'''
header+='\\title{'+esc(lines[0][2:])+'}\n\\author{Research manuscript}\n\\date{14 November 2026}\n\\begin{document}\\maketitle\n'
(P/'main.tex').write_text(header+'\n'.join(out)+'\n\\end{document}\n')
