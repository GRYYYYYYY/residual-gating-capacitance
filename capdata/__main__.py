"""List, download and verify versioned research artifacts without Git LFS."""
import argparse
import hashlib
import gzip
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import urllib.request
from . import ROOT, catalog

REPOSITORY='GRYYYYYYY/residual-gating-capacitance'
TAG='v1.0.0'

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def packages():return json.loads((ROOT/'database/packages.json').read_text())
def files():
    result=json.loads((ROOT/'database/files.json').read_text())
    extra=ROOT/'database/files-extended.json.gz'
    if extra.exists():
        with gzip.open(extra,'rt') as f:result.extend(json.load(f))
    return result

def package_key(name):
    matches=[k for k in packages() if k==name or k==name+'-'+TAG]
    if len(matches)!=1:raise ValueError(f'Unknown package {name}; choose {list(packages())}')
    return matches[0]

def extract_verified(archive,root,members):
    """Reject traversal, links, extra files, changed payloads and conflicting files."""
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    expected={x['path']:x for x in members}
    with tempfile.TemporaryDirectory(prefix='.rg-extract-',dir=root) as tmp:
        staging=Path(tmp)
        with tarfile.open(archive,'r:gz') as t:
            seen=set()
            for m in t:
                p=PurePosixPath(m.name)
                if p.is_absolute() or '..' in p.parts or not m.isfile() or m.name not in expected or m.name in seen:
                    raise ValueError(f'Unsafe/unexpected archive member: {m.name}')
                seen.add(m.name);spec=expected[m.name]
                if m.size!=spec['bytes']:raise ValueError(f'Size mismatch: {m.name}')
                dest=staging/m.name;dest.parent.mkdir(parents=True,exist_ok=True)
                with t.extractfile(m) as src,dest.open('wb') as dst:shutil.copyfileobj(src,dst)
                if digest(dest)!=spec['sha256']:raise ValueError(f'Hash mismatch: {m.name}')
            if seen!=set(expected):raise ValueError('Archive is incomplete')
        # Validate the whole archive before modifying the destination.
        for name,spec in expected.items():
            target=root/name
            if root not in target.resolve().parents:raise ValueError('Destination escapes root')
            if target.exists() and digest(target)!=spec['sha256']:
                raise FileExistsError(f'Conflicting local file (not overwritten): {target}')
        for name in expected:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():os.replace(staging/name,target)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    p=sub.add_parser('info');p.add_argument('dataset')
    p=sub.add_parser('fetch');p.add_argument('packages',nargs='*');p.add_argument('--all',action='store_true');p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--from-dir',type=Path)
    p=sub.add_parser('verify');p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--all',action='store_true');p.add_argument('--package')
    args=parser.parse_args()
    if args.command=='list':
        for key,d in catalog()['datasets'].items():
            present=(Path(os.environ.get('RG_DATA_ROOT',ROOT))/d['path']).exists()
            print(f'{key:35} {"ready" if present else "not downloaded":15} {d.get("tables",d.get("count",""))!s:>6}  {d["role"]}')
        return
    if args.command=='info':print(json.dumps(catalog()['datasets'][args.dataset],indent=2,ensure_ascii=False));return
    if args.command=='fetch':
        keys=list(packages()) if args.all else [package_key(n) for n in args.packages]
        if not keys:parser.error('Name a package or use --all')
        cache=args.root/'.cache/release';cache.mkdir(parents=True,exist_ok=True)
        for key in keys:
            spec=packages()[key];archive=(args.from_dir/spec['file']) if args.from_dir else cache/spec['file']
            if not archive.exists():
                if args.from_dir:raise FileNotFoundError(archive)
                url=f'https://github.com/{REPOSITORY}/releases/download/{TAG}/{spec["file"]}'
                print('Downloading',url,flush=True)
                part=archive.with_suffix('.part')
                with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'residual-gating-capdata/1.0'}),timeout=120) as src,part.open('wb') as dst:shutil.copyfileobj(src,dst)
                os.replace(part,archive)
            if digest(archive)!=spec['sha256']:raise ValueError(f'Archive hash mismatch: {archive}')
            extract_verified(archive,args.root,[r for r in files() if r['package']==key])
            print('Verified and installed',key,flush=True)
    else:
        selected=files()
        if args.package:
            key=package_key(args.package);selected=[f for f in selected if f['package']==key]
        checked=0;missing=[]
        for f in selected:
            p=args.root/f['path']
            if not p.exists():missing.append(f['path']);continue
            if digest(p)!=f['sha256']:raise ValueError(f'Hash mismatch: {p}')
            checked+=1
        print(json.dumps(dict(verified=checked,not_downloaded=len(missing))))
        if (args.all or args.package) and missing:raise SystemExit('Requested package files are missing')
        if not checked:raise SystemExit('No artifact files installed')

if __name__=='__main__':main()
