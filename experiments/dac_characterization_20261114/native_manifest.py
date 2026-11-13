"""Hash complete local native output and collect measured downstream costs."""
import json,csv
from common import *
R=ROOT/'results/dac_characterization_20261114'
out=R/'summary'
assert json.loads((out/'downstream_status.json').read_text())['complete']
entries=[];costs=[]
for p in sorted((R/'downstream/native').rglob('*')):
 if not p.is_file():continue
 entries.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)))
 if p.name=='COMPLETED.json':
  r=json.loads(p.read_text());f=json.loads((p.parent/'FROZEN.json').read_text())
  costs.append(dict(case=f['case'],variant=f['variant'],wall_seconds=r['wall_seconds'],extraction_seconds=r['extraction_seconds'],cpu_seconds=None,threads=1,status=r['status'],wall_measurement=r.get('wall_measurement','measured subprocess wall'),receipt=str(p.relative_to(ROOT))))
assert len(costs)==248
(out/'native_artifact_manifest.json').write_text(json.dumps(dict(files=entries,total_bytes=sum(e['bytes'] for e in entries)),indent=2))
with (out/'native_cost.csv').open('w') as f:
 w=csv.DictWriter(f,costs[0]);w.writeheader();w.writerows(costs)
print('native artifacts',len(entries),'bytes',sum(e['bytes'] for e in entries))
