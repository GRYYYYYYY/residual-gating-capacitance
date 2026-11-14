from pathlib import Path
import hashlib,zipfile,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=sorted(p for p in P.rglob('*') if p.is_file() and p.suffix in ['.md','.py','.csv','.json','.tex','.pdf','.png'])
manifest=''.join(f'{sha(p)}  {p.relative_to(ROOT)}\n' for p in files)
a=ROOT/'review/DAC_EVIDENCE_CLOSEOUT_20261114.zip'
with zipfile.ZipFile(a,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.relative_to(ROOT))
 z.writestr('SHA256SUMS',manifest)
 z.writestr('README.txt','Editorial closeout only, based on dce58bed002dd7440f963bcb21f28859bfcc6973. Read DAC_REWRITE.md/main.pdf and PUBLICATION_ASSESSMENT.md in paper/dac_evidence_closeout_20261114/. No new models, predictions, timing, field solves, transfer or native runs. Old large artifacts are referenced by the manuscript and input hashes, not duplicated.\n')
with zipfile.ZipFile(a) as z:
 assert z.testzip() is None
 for l in z.read('SHA256SUMS').decode().splitlines():h,p=l.split('  ',1);assert hashlib.sha256(z.read(p)).hexdigest()==h
hfile=a.with_suffix('.sha256');hfile.write_text(f'{sha(a)}  {a.name}\n')
subprocess.run(['git','add',*[str(p.relative_to(ROOT)) for p in files],str(hfile.relative_to(ROOT))],cwd=ROOT,check=True)
subprocess.run(['git','add','-f',str(a.relative_to(ROOT))],cwd=ROOT,check=True)
print(a,a.stat().st_size,sha(a))
