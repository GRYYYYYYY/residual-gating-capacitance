"""Download pinned upstream rules and reproduce the exact public table/split file."""
import argparse,concurrent.futures,hashlib,json,urllib.request
from pathlib import Path
from pdkcap.common import ROOT
from pdkcap.data import prepare
from pdkcap.source_imports.openrcx import parse_openrcx
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--raw-root',type=Path,help='Optional existing input directory; verified read-only')
a=p.parse_args();lock=json.loads((ROOT/'configs/public_sources.lock.json').read_text());a.output.mkdir(parents=True,exist_ok=False)
def fetch(s):
 path=(a.raw_root/s['path']) if a.raw_root else (a.output/'upstream'/s['path'])
 if a.raw_root:blob=path.read_bytes()
 else:
  req=urllib.request.Request(s['url'],headers={'User-Agent':'PDKCap-reproduction/1.0'})
  with urllib.request.urlopen(req,timeout=60) as r:blob=r.read()
 assert hashlib.sha256(blob).hexdigest()==s['sha256'],s['source_id']
 if not a.raw_root:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)
 return [t.to_dict() for t in parse_openrcx(path,source_id=s['source_id'],process_id=s['process_id'],corner_id=s['corner_id'],process_features=lock['process_features'][s['process_id']])]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 rows=[r for group in pool.map(fetch,lock['sources']) for r in group]
tables,audit=prepare(rows)
payload=''.join(json.dumps(t,sort_keys=True)+'\n' for t in tables).encode()
digest=hashlib.sha256(payload).hexdigest()
assert digest==lock['expected_tables_sha256'],('reconstruction mismatch',digest)
(a.output/'tables.jsonl').write_bytes(payload)
(a.output/'verification.json').write_text(json.dumps({'sha256':digest,'tables':len(tables),'upstream_files':len(lock['sources']),'audit':audit},indent=2))
print(json.dumps({'status':'exact_reconstruction_passed','tables':len(tables),'sha256':digest}))
