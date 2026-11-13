import gzip,json,collections
from common import *
from pdkcap.metrics import summarize
s=sys.argv[1];p=ROOT/f'results/dac_characterization_20261114/validation_{s}/records.jsonl.gz'
rows=[json.loads(l) for l in gzip.open(p,'rt')];assert all(r['status']=='ok' for r in rows)
groups=collections.defaultdict(list)
for r in rows:groups[r['method']].append(r)
scores={m:summarize(rs)['nrmse'] for m,rs in groups.items()}
best=min((m for m in scores if m.startswith('gp_')),key=scores.get)
from pdkcap.round3_experts import GP_CONFIGS
bytable=collections.defaultdict(list)
for r in groups['anchor']:bytable[r['table_id']].append(r)
values=[]
for rs in bytable.values():
    r=max((r for r in rs if r['budget']<=8),key=lambda r:r['budget']);sy=np.array(r['squared_truth']);se=np.array(r['squared_error']);
    if (sy>0).any():values.append(float(np.mean(np.sqrt(se[sy>0]/sy[sy>0]))))
sel=dict(gp=list(GP_CONFIGS[best]),gp_name=best,validation_scores=scores,thresholds=np.quantile(values,[.25,.5,.75]).tolist(),threshold_rule='source-validation per-table anchor NRMSE quantiles at B<=8',pruned_selected=scores['pruned']<=scores['full'],validation_hash=sha(p),confirmation_seen=False)
write(HERE/f'selected_{s}.json',sel);print(s,sel,flush=True)
