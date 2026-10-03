"""Paired public-table group bootstrap, identical to the published estimator.
Pointwise 95% intervals, not simultaneous/multiplicity-adjusted intervals.
"""
import json
from pathlib import Path
from run_controls import HERE,ROOT,ARCHIVE
from unified.paired import group_accumulator,prepare,bootstrap_delta
from unified.regime import REGIMES

def main():
 (HERE/'generated/tables').mkdir(parents=True,exist_ok=True)
 paths=[ROOT/'runs/conf_public_holdout/records.jsonl.gz',HERE/'scores/public/learned_confirmation.jsonl.gz']
 methods=['sace_r_holdout','residual','binary']
 out={}
 for regime,segments in REGIMES.items():
  accumulator=group_accumulator(paths,methods,segments=segments)
  for protocol in (['mcar','block'] if regime=='inside' else ['mcar','block','extrapolation']):
   prepared=prepare(accumulator,protocol,.3)
   for alternative in ['residual','binary']:
    result=bootstrap_delta(prepared,'sace_r_holdout',alternative,replicates=2000,seed=20260926)
    out[f'{regime}/{protocol}/{alternative}']=result
 (HERE/'public_bootstrap.json').write_text(json.dumps(out,indent=2))
 lines=[r'\scriptsize',r'\setlength{\tabcolsep}{3pt}',r'\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}llrr@{}}\toprule',r'Regime / mask & Comparator & $\Delta$NRMSE & Paired 95\% interval \\',r'\midrule']
 for name,row in out.items():
  reg,prot,method=name.split('/')
  label=('In-support' if reg=='inside' else 'Out-of-support')+' / '+dict(mcar='random',block='block',extrapolation='extrapolation')[prot]
  comparison={'residual':'Ungated residual','binary':'Binary gate'}[method]
  lines.append(f"{label} & {comparison} & {row['delta']:+.4f} & [{row['low']:+.4f}, {row['high']:+.4f}] "+r'\\')
 lines.append(r'\bottomrule\end{tabular*}')
 (HERE/'generated/tables/supp_control_bootstrap.tex').write_text('\n'.join(lines)+'\n')
 print(json.dumps(out),flush=True)
if __name__=='__main__':main()
