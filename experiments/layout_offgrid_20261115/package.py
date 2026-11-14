"""Package reviewable results; raw meshes/native databases remain hash-indexed."""
from pathlib import Path
import hashlib,json,subprocess,zipfile,shutil
R=Path(__file__).resolve().parents[2];O=R/'results/layout_offgrid_20261115';P=R/'paper/dac_layout_query_revision'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
raw=[]
for p in sorted(O.rglob('*')):
 if p.is_file() and (p.suffix in ['.msh','.spef','.o','.a'] or p.name in ['openroad-trace','trace.tsv','query_manifest.jsonl']):
  raw.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p),distribution='local-only; reproducible or input-license dependent'))
(O/'RAW_ARTIFACTS.json').write_text(json.dumps(dict(root=str(R),files=raw,total_bytes=sum(x['bytes'] for x in raw)),indent=2))
# Plain text inspection and task-specific assertions are independent of LaTeX.
summary=json.loads((O/'COMPLETED.json').read_text());assert summary['direct_FEM_formal_queries']==71
assert len(json.loads((O/'reference_formal_ledger.json').read_text()))==213
assert all(r['passed'] for r in json.loads((O/'reference_convergence.json').read_text()))
assert json.loads((O/'native_validation.json').read_text())['summary']['passed']
# Select explicit paths; never include the original CTFs, model weights or tools.
files=[]
for root in [P,R/'docs/layout_offgrid_20261115',R/'experiments/layout_offgrid_20261115',O]:
 for p in sorted(root.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(R)
  if any(x in rel.parts for x in ['__pycache__','pdf_preview']):continue
  if p.suffix in ['.msh','.spef','.o','.a','.aux','.log','.out','.fls','.fdb_latexmk','.pyc']:continue
  if p.name in ['openroad-trace','trace.tsv','query_manifest.jsonl','RAW_ARTIFACTS.json','DELIVERY_MANIFEST.json','SHA256SUMS']:continue
  if p.name.startswith('partial_unscored_'):continue
  files.append(p)
files += [O/'RAW_ARTIFACTS.json',R/'unified/queries.py']
manifest=dict(base_head='78b51129f78691e0e581e906871af5ca226f1599',status=summary,files=[dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
(O/'DELIVERY_MANIFEST.json').write_text(json.dumps(manifest,indent=2));files.append(O/'DELIVERY_MANIFEST.json')
review=R/'review/DAC_LAYOUT_QUERY_20261115.zip'
with zipfile.ZipFile(review,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(R))
review.with_suffix('.sha256').write_text(sha(review)+'  '+review.name+'\n')
(P/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(P))+'\n' for p in sorted(P.rglob('*')) if p.is_file() and p.suffix in ['.tex','.pdf','.bib','.py','.md','.csv','.json','.png'] and p.name!='SHA256SUMS'))
# Accessible copy beside the user's original task package.
dest=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/test-v1/paper_v6/paper_v6_overleaf/gpt_docs')
shutil.copy2(review,dest/review.name);shutil.copy2(review.with_suffix('.sha256'),dest/review.with_suffix('.sha256').name)
print(json.dumps(dict(review=str(review),bytes=review.stat().st_size,sha256=sha(review),files=len(files),local_raw_bytes=sum(x['bytes'] for x in raw)),indent=2))
