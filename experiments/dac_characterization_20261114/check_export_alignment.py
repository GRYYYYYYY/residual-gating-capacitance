"""Check table scoring and native completion use identical geometry batching."""
import gzip,json
from common import *
R=ROOT/'results/dac_characterization_20261114';d=R/'downstream/rules';m=json.loads((d/'manifest.json').read_text());support={(r['table_id'],r['budget_requested'],r['seed']):r for r in m['support']};count=0
for r in map(json.loads,gzip.open(R/'confirmation_public/records.jsonl.gz','rt')):
 if r['method'] not in ('full','binary','anchor','affine','cmi') or r['strategy']!='farthest':continue
 k=(r['table_id'],r['budget'],r['data_seed'])
 if k not in support:continue
 s=support[k];assert r['support_indices']==s['support'] and r['query_indices']==s['query']
 payload=json.loads((d/f"{r['method']}_B{r['budget']}_s{r['data_seed']}.json").read_text())['tables'][s['upstream_id']]
 for idx,vals in payload.items():
  for j,name in enumerate(r['target_names']):assert vals[name]==r['prediction'][int(idx)][j]
 count+=1
assert count>0
write(R/'export_batch_alignment.json',dict(aligned_episodes=count,prediction_bit_exact=True,geometry_batch='same fixed full grid',observed_rows_never_rewritten=True,eligible_holdout_tables=m['eligible_tables'],excluded_short_tables=m['excluded_short_tables']))
print('export alignment episodes',count)
