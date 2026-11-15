"""Lossless payload distribution and lightweight, commit-bound review bundle."""
from common import *
import gzip,subprocess,zipfile,argparse
D=R/'docs/pex_kernel_revision'
PREFIXES=['docs/pex_kernel_revision/','experiments/pex_kernel_revision/','results/pex_kernel_revision/','paper/dac_layout_query_revision/']
def paths():
 items=subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=R,text=True).split('\0')
 return sorted({x for x in items if any(x.startswith(p) for p in PREFIXES) and (R/x).is_file() and not x.endswith('ARTIFACT_MANIFEST.json')})
def prepare():
 assert read(O/'CHECKS.json')['passed'],'Require completed checks before sealing artifacts'
 payloads=[]
 for p in sorted((O/'payloads').glob('*.tsv')):
  data=p.read_bytes();g=p.with_suffix('.tsv.gz')
  with g.open('wb') as f:
   with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(data)
  assert gzip.decompress(g.read_bytes())==data
  payloads.append(dict(path=str(g.relative_to(R)),sha256=sha(g),uncompressed_sha256=sha(p),bytes=len(data)))
 write(O/'payload_distribution.json',dict(compression='gzip,mtime=0; lossless original TSV',payloads=payloads))
 manifest=dict(base_commit='a519539fee8a763c74e1db61427fdd02d85511ca',files=[dict(path=x,bytes=(R/x).stat().st_size,sha256=sha(R/x)) for x in paths()],excluded='Local binaries, archives, full copied translation units, original payload TSVs (gzip copies included), SPEFs, pointer-rich getter logs, slot dumps, TeX intermediates and previews. Manifest excludes itself. Earlier immutable dependencies remain in the repository or documented local environment.')
 write(D/'ARTIFACT_MANIFEST.json',manifest);print('manifest files',len(manifest['files']))
def bundle():
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=R,text=True).strip(),'Commit reviewed artifacts before bundling'
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
 manifest=read(D/'ARTIFACT_MANIFEST.json')
 for x in manifest['files']:assert sha(R/x['path'])==x['sha256'],x['path']
 target=O/'review_bundle';target.mkdir(exist_ok=True)
 dest=target/f'DAC_PEX_KERNEL_REVISION_RESULTS_{head[:12]}.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for x in paths()+['docs/pex_kernel_revision/ARTIFACT_MANIFEST.json']:z.write(R/x,x)
  z.writestr('RELEASE_COMMIT.txt',head+'\n')
  z.writestr('README_REVIEW.txt','Formal papers: paper/dac_layout_query_revision/main.pdf and extended.pdf\nStart with docs/pex_kernel_revision/RESULTS.md and REPRODUCE.md.\nThe relative-path manifest contains SHA-256 hashes. For full replay, check out the recorded commit in GRYYYYYYY/residual-gating-capacitance; earlier frozen dependencies are intentionally not duplicated in this lightweight archive.\n')
 receipt=dict(commit=head,path=str(dest),sha256=sha(dest),bytes=dest.stat().st_size)
 write(target/'PACKAGE.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');args=ap.parse_args()
 prepare() if args.prepare else bundle()
