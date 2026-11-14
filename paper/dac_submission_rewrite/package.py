"""Bundle the manuscript and its small derivations, never raw training assets."""
from pathlib import Path
import hashlib,json,zipfile
P=Path(__file__).resolve().parent;R=P.parents[1]
ignored={'.aux','.log','.out','.blg','.fls','.fdb_latexmk'}
files=[p for p in sorted(P.rglob('*')) if p.is_file() and p.suffix not in ignored and '__pycache__' not in p.parts and p.name not in {'FILES.json','SHA256SUMS'}]
hashes={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(P/'FILES.json').write_text(json.dumps([{'path':k,'bytes':(P/k).stat().st_size,'sha256':v} for k,v in hashes.items()],indent=2)+'\n')
(P/'SHA256SUMS').write_text(''.join(v+'  '+k+'\n' for k,v in hashes.items()))
z=R/'review/DAC_FORMAL_PAPER_REWRITE_20261114.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
 for p in files+[P/'FILES.json',P/'SHA256SUMS']:out.write(p,arcname='dac_submission_rewrite/'+str(p.relative_to(P)))
with zipfile.ZipFile(z) as inp:
 assert inp.testzip() is None
 for p,h in hashes.items():assert hashlib.sha256(inp.read('dac_submission_rewrite/'+p)).hexdigest()==h
h=hashlib.sha256(z.read_bytes()).hexdigest();z.with_suffix('.sha256').write_text(h+'  '+z.name+'\n')
print(json.dumps({'archive':str(z),'bytes':z.stat().st_size,'sha256':h,'files':len(files)+2},indent=2))
