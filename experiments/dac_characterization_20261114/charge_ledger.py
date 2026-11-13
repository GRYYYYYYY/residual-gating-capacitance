"""One row per unique paid geometry along each registered sampling trajectory.
Do not sum across methods or cumulative budget snapshots as new solver work.
"""
import csv,gzip,json,collections
from common import *
R=ROOT/'results/dac_characterization_20261114'
index={}
for r in csv.DictReader((R/'geometry_cost_index.csv').open()):index[r['table_id'],tuple(json.loads(r['coordinates']))]=r
charges=[]
for s in MODELS:
 ts={t['table_id']:t for t in tables(s,'confirmation')};latest={}
 for r in map(json.loads,gzip.open(R/f'confirmation_{s}/records.jsonl.gz','rt')):
  k=(r['table_id'],r['data_seed'],r['strategy'])
  if k not in latest or latest[k]['budget']<r['budget']:latest[k]=r
 for (tid,seed,strategy),r in latest.items():
  t=ts[tid];assert len(set(r['history']))==r['budget']
  for step,i in enumerate(r['history'],1):
   coord=t['coordinates'][i];entry=index.get((tid,tuple(coord)))
   charges.append(dict(setting=s,table_id=tid,data_seed=seed,strategy=strategy,purchase_ordinal=step,candidate_index=i,coordinates=json.dumps(coord),geometry_id=None if entry is None else entry['geometry_id'],fine_record_id=None if entry is None else entry['fine_id'],fine_cpu_seconds=None if entry is None else entry['fine_cpu_seconds'],fine_excitations=None if entry is None else entry['fine_excitations'],validated_cpu_seconds=None if entry is None else entry['validated_cpu_seconds'],validated_excitations=None if entry is None else entry['validated_excitations'],ledger_sha256=None if entry is None else entry['ledger_sha256'],unique_query_charge=1,components_returned=len(t['target_names']),cost_kind='simulated_rule_entry' if entry is None else 'recorded-cost replay',shared_by='all main predictors' if strategy=='farthest' else 'anchor,full'))
p=R/'query_charge_ledger.csv'
with p.open('x') as f:w=csv.DictWriter(f,charges[0]);w.writeheader();w.writerows(charges)
write(R/'query_charge_verification.json',dict(unique_trajectory_purchases=len(charges),counts='not additive across methods, settings or overlapping physical views',components_counted_once=True,no_sealed_Q_purchase=True,history_unique=True))
print('unique trajectory purchases',len(charges))
