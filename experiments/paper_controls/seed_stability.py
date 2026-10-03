import json,csv
from pathlib import Path
from run_controls import HERE
CELLS=['inside/mcar','inside/block','outside/mcar','outside/block','outside/extrapolation']

def main():
 results={};rows=[]
 for domain in ['public','reference','to_asap7']:
  d=json.loads((HERE/'scores'/domain/'learned_summary.json').read_text())
  summary={}
  for variant in ['residual','binary']:
   wins={cell:[d[f'full_replayed_seed{s}'][cell]<d[f'{variant}_seed{s}'][cell] for s in range(3)] for cell in CELLS}
   summary[variant]=dict(full_seed_pair_wins=sum(sum(w) for w in wins.values()),total_seed_pairs=15,full_wins_all_three_seeds_in=[c for c,w in wins.items() if all(w)],wins_by_condition=wins)
  results[domain]=summary
  for variant in ['residual','binary','full_replayed']:
   for cell in CELLS:
    regime,protocol=cell.split('/')
    for seed in range(3):rows.append([domain,variant,regime,protocol,seed,d[f'{variant}_seed{seed}'][cell]])
    rows.append([domain,variant,regime,protocol,'ensemble',d[variant][cell]])
 (HERE/'seed_stability.json').write_text(json.dumps(results,indent=2))
 with (HERE/'control_seed_scores.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['setting','model','regime','mask_protocol','training_seed','nrmse']);w.writerows(rows)
 print(json.dumps(results,indent=2))
if __name__=='__main__':main()
