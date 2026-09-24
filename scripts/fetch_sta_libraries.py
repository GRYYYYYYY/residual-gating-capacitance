"""Fetch exact Liberty and layer-RC inputs for the recorded fixed-layout STA."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--platform');p.add_argument('--output',type=Path,default=ROOT/'upstream/flow');a=p.parse_args()
lock=json.loads((ROOT/'configs/sta_sources.lock.json').read_text())
for item in lock['files']:
 if a.platform and not item['path'].startswith('platforms/'+a.platform+'/'):continue
 dest=a.output/item['path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():blob=dest.read_bytes()
 else:
  with urllib.request.urlopen(urllib.request.Request(item['url'],headers={'User-Agent':'residual-gating-artifacts/1.0'}),timeout=90) as r:blob=r.read()
 if hashlib.sha256(blob).hexdigest()!=item['sha256']:raise ValueError('Input hash mismatch: '+item['path'])
 if not dest.exists():dest.write_bytes(blob)
 print('verified',item['path'],flush=True)
