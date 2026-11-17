"""Verify immutable pre-revision snapshot against current original inputs."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';D=R/'docs/dac_main13_integrated_revision'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify():
 snap=Path(json.loads((D/'snapshot.json').read_text())['path']);receipt=O/'tests/original_preservation.json';fingerprints=O/'original_input_fingerprints.json'
 cached=False
 if receipt.exists() and fingerprints.exists():
  fp=json.loads(fingerprints.read_text())
  if all(Path(p).exists() and [Path(p).stat().st_size,Path(p).stat().st_mtime_ns]==st for p,st in fp.items()):
   if json.loads(receipt.read_text())['old_checkpoints']==27:
    print('REUSE verified original hashes: unchanged size/mtime for',len(fp),'files',flush=True);return json.loads(receipt.read_text())
   cached=True
 hashes=json.loads((O/'original_input_hashes.json').read_text()) if cached else {};fp=fp if cached else {};n=json.loads(receipt.read_text())['snapshotted_sources_results_checked'] if cached else 0
 def compare(p,target):
  nonlocal n
  assert target.exists() and sha(p)==sha(target),('original input changed',str(target));hashes[str(target)]=sha(target);fp[str(target)]=[target.stat().st_size,target.stat().st_mtime_ns];n+=1
 for group in ([] if cached else ['configs','experiments']):
  for p in (snap/group).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts:compare(p,R/p.relative_to(snap))
 for name in ([] if cached else ['pex_kernel_revision','dac_characterization_20261114','downstream_kernel_comparison_20261117','runtime_accuracy_20261115']):
  for p in (snap/'evidence'/name).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts:compare(p,R/'results'/name/p.relative_to(snap/'evidence'/name))
  print('PRESERVED',name,n,flush=True)
 ck=json.loads((snap/'evidence/checkpoint_manifest.json').read_text())
 for r in ck:
  p=Path(r['path']);assert sha(p)==r['sha256'];hashes[str(p)]=r['sha256'];fp[str(p)]=[p.stat().st_size,p.stat().st_mtime_ns]
 full={Path(r['path']).parent.name:Path(r['path']).parent for r in ck};controls=Path(json.loads((R/'experiments/dac_characterization_20261114/paths.json').read_text())['control_root'])/'runs';copied=list((snap/'evidence/checkpoints').glob('*/*/checkpoint.pt'));assert len(copied)==27
 for p in copied:
  target=full.get(p.parent.name,controls/p.parent.name)
  for q in p.parent.iterdir():
   if q.is_file():compare(q,target/q.name)
 original=json.loads((D/'snapshot.json').read_text())['paper_sha256'];assert sha(snap/'paper/dac_layout_query_revision/main.pdf')==original
 result=dict(status='PASS',snapshotted_sources_results_checked=n,old_checkpoints=len(copied),original_pdf_sha256=original,snapshot=str(snap),reuse_policy='hashes are reused only while original input sizes and nanosecond mtimes remain unchanged')
 (O/'original_input_hashes.json').write_text(json.dumps(hashes,indent=2));fingerprints.write_text(json.dumps(fp,indent=2));receipt.write_text(json.dumps(result,indent=2));print('PRESERVATION_PASS',n,len(copied),flush=True);return result
if __name__=='__main__':verify()
