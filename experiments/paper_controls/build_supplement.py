"""Generate appendix tables directly from recorded scores (no hand-entered results)."""
import json,gzip
from pathlib import Path
from run_controls import HERE,ROOT,ARCHIVE
from score_controls import FULL,scores
from unified.aggregate import add_records,mask_macro_nrmse
from unified.regime import regroup

PAPER=HERE/'generated'
(PAPER/'tables').mkdir(parents=True,exist_ok=True)
CELLS=['inside/mcar','inside/block','outside/mcar','outside/block','outside/extrapolation']
LABEL={'public':'Public rules','reference':'FEM reference','to_asap7':'Transfer to ASAP7'}

def table(data,names):
 lines=[r'\scriptsize',r'\setlength{\tabcolsep}{3pt}',r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lrrrrr@{}}\toprule',r' & \multicolumn{2}{c}{In-support} & \multicolumn{3}{c}{Out-of-support} \\',r'\cmidrule(lr){2-3}\cmidrule(lr){4-6}',r'Method & Random & Block & Random & Block & Extrap. \\',r'\midrule']
 for i,(domain,rows) in enumerate(data.items()):
  if i:lines.append(r'\midrule')
  lines.append(r'\multicolumn{6}{@{}l}{\textit{'+LABEL[domain]+r'}} \\')
  best={c:min(v[c] for v in rows.values()) for c in CELLS}
  for name,values in rows.items():
   cells=[]
   for c in CELLS:
    v=values[c];s=f'{v:.4f}'
    if v==best[c]:s=r'\textbf{'+s+'}'
    elif name=='full' and sum(other[c]<v for other in rows.values())==1:s=r'\underline{'+s+'}'
    cells.append(s)
   label=names.get(name,name)
   if name=='full':label=r'\textbf{'+label+'}'
   lines.append(label+' & '+' & '.join(cells)+r' \\')
 lines.append(r'\bottomrule\end{tabular*}')
 return '\n'.join(lines)+'\n'

def main():
 numerical={};learned={};raw={}
 for domain,(run,fullmethod) in FULL.items():
  orig=ARCHIVE/'runs'/run/'records.jsonl.gz'
  full=scores(orig,[fullmethod,fullmethod+'_anchor'])
  pred=full[fullmethod];anchor=full[fullmethod+'_anchor']
  affine=json.loads((HERE/'scores'/domain/'affine_summary.json').read_text());affine=next(iter(affine.values()))
  numerical[domain]={'anchor':anchor,'affine':affine,'full':pred}
  raw[domain]=dict(full=pred,anchor=anchor,affine=affine)
  path=HERE/'scores'/domain/'learned_summary.json'
  if path.exists():
   new=json.loads(path.read_text());learned[domain]={'residual':new['residual'],'binary':new['binary'],'full':pred};raw[domain].update(new)
 names={'anchor':'Support anchor','affine':'Local affine (validation-selected)','full':'Full routing (reported ensemble)','residual':'Transformer + ungated residual','binary':'Anchor/neural binary gate'}
 (PAPER/'tables/supp_affine_control.tex').write_text(table(numerical,names))
 if len(learned)==3:(PAPER/'tables/supp_matched_controls.tex').write_text(table(learned,names))
 (HERE/'comparison_summary.json').write_text(json.dumps(raw,indent=2))
 print(json.dumps({d:{n:sum(v[c]<raw[d]['full'][c] for c in CELLS) for n,v in rows.items()} for d,rows in learned.items()},indent=2))
if __name__=='__main__':main()
