"""Package the small review, never weights or native logs. Verify ZIP contents."""
import argparse,csv,hashlib,json,zipfile,datetime
from pathlib import Path
D=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,default=D.parent/'DAC_REVIEW_20261114_269a86b.zip');args=ap.parse_args()
assert not args.archive.exists(),'Keep the previous archive; use --archive with a fresh filename.'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
payload=[p for p in sorted(D.iterdir()) if p.is_file() and p.name not in ('FILES.csv','SHA256SUMS','build.log')]
assert all(p.suffix in ('.csv','.json','.md','.pdf','.py') for p in payload)
assert json.loads((D/'verification.json').read_text())['status']=='PASS'
with (D/'FILES.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,['file','bytes','sha256'],lineterminator='\n');w.writeheader()
 for p in payload:w.writerow(dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)))
(D/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in payload+[D/'FILES.csv']))
allfiles=payload+[D/'FILES.csv',D/'SHA256SUMS']
with zipfile.ZipFile(args.archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in allfiles:z.write(p,'DAC_REVIEW_20261114/'+p.name)
with zipfile.ZipFile(args.archive) as z:
 assert z.testzip() is None
 for p in allfiles:assert hashlib.sha256(z.read('DAC_REVIEW_20261114/'+p.name)).hexdigest()==sha(p)
 assert len(z.namelist())==len(allfiles)
info=dict(archive=str(args.archive.resolve()),bytes=args.archive.stat().st_size,sha256=sha(args.archive),files=len(allfiles),payload_uncompressed_bytes=sum(p.stat().st_size for p in allfiles),start_commit='269a86b15a5619400447266c186485a641b8a8ef',manifest='DAC_REVIEW_20261114/FILES.csv',hash_file='DAC_REVIEW_20261114/SHA256SUMS',integrity='ZIP CRC and every member SHA verified; FILES excludes itself/SHA256SUMS, SHA256SUMS includes FILES and excludes itself')
args.archive.with_suffix('.sha256').write_text(f"{info['sha256']}  {args.archive.name}\n")
args.archive.with_suffix('.manifest.json').write_text(json.dumps(info,indent=2)+'\n')
print(json.dumps(info,indent=2))
