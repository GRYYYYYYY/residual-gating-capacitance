"""Fetch exact original material inputs from upstream; this repo does not bundle them."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
from pdkcap.common import ROOT
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
lock=json.loads((ROOT/'configs/reference_sources.lock.json').read_text())
for s in lock['sources']:
 with urllib.request.urlopen(s['url'],timeout=60) as r:data=r.read()
 assert hashlib.sha256(data).hexdigest()==s['sha256'],s['name']
 (a.output/s['name']).write_bytes(data)
print('Original CTF hashes verified. Upstream terms remain applicable; no redistribution license is granted here.')
