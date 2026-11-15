"""Compact review artifacts; generated SPEFs/rules/binaries stay local."""
from common_runtime import *
import gzip,shutil,zipfile
P=R/'paper/dac_layout_query_revision'
def local_only(p):
    rel=p.relative_to(O)
    return p.suffix in ['.spef','.so','.rules'] or p.name=='native_lookup' or rel.parts[0] in ['rules','pdf_preview'] or p.name.startswith('cold_worker_')
def main():
    assert read(O/'CHECKS.json')['passed']
    for p in sorted(O.iterdir()):
        if p.name.startswith(('timing_','predictions_','cnp_combined_initial_','cached_union_initial_')) and p.suffix in ['.csv','.jsonl']:
            with p.open('rb') as src,(O/(p.name+'.gz')).open('wb') as dst:
                with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0) as packed:shutil.copyfileobj(src,packed)
    files=[]
    for p in sorted(O.rglob('*')):
        if not p.is_file() or p.name in ['ARTIFACTS.json','PACKAGE.json']:continue
        files.append(dict(path=str(p.relative_to(R)),bytes=p.stat().st_size,sha256=sha(p),local_only=local_only(p),compressed_duplicate=p.suffix in ['.csv','.jsonl'] and Path(str(p)+'.gz').exists()))
    write(O/'ARTIFACTS.json',dict(files=files,large_artifact_policy='SPEFs, rewritten rule files, binaries and redundant uncompressed timing/prediction files remain local; no model weights or new meshes uploaded'))
    paths=[]
    for root in [R/'experiments/runtime_accuracy_20261115',R/'docs/runtime_accuracy_20261115',P]:
        paths.extend(p for p in root.rglob('*') if p.is_file() and p.suffix not in ['.aux','.log','.out','.fls','.fdb_latexmk','.pyc'] and '__pycache__' not in p.parts)
    paths.extend(R/r['path'] for r in files if not r['local_only'] and not r['compressed_duplicate'])
    paths.append(O/'ARTIFACTS.json');dest=R/'review/DAC_RUNTIME_ACCURACY_20261115.zip';dest.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(set(paths)):z.write(p,str(p.relative_to(R)))
    write(O/'PACKAGE.json',dict(path=str(dest.relative_to(R)),bytes=dest.stat().st_size,sha256=sha(dest),contains_weights=False,contains_new_meshes=False,contains_spefs=False))
    print(dest,round(dest.stat().st_size/1e6,3),'MB',sha(dest))
if __name__=='__main__':main()
