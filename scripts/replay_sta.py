"""Replay saved SPEFs on the exact shared ODB/SDC, without extraction or rerouting."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--case',default='gf180/ibex');p.add_argument('--missing',type=int,choices=[30,50],default=50)
p.add_argument('--openroad',default=os.environ.get('OPENROAD_EXE','openroad'));p.add_argument('--flow',type=Path,default=ROOT/'upstream/flow')
p.add_argument('--outdir',type=Path,default=ROOT/'results/sta_replay');p.add_argument('--threads',type=int,default=2);a=p.parse_args()
cases=json.loads((ROOT/'database/sta_cases.json').read_text());case=cases[a.case];platform,design=a.case.split('/')
lock=json.loads((ROOT/'configs/sta_sources.lock.json').read_text())
for item in lock['files']:
 if item['path'].startswith('platforms/'+platform+'/'):
  f=a.flow/item['path']
  if not f.is_file():raise FileNotFoundError(f'{f}: run scripts/fetch_sta_libraries.py --platform {platform}')
  if sha(f)!=item['sha256']:raise ValueError(f'Hash mismatch: {f}')
# Check exact ODB and SDC provenance against the release member manifest.
from sys import path as searchpath
searchpath.insert(0,str(ROOT))
from capdata.__main__ import files
expected={r['path']:r for r in files()}
for key in ['odb','sdc']:
 f=ROOT/case[key]
 if not f.is_file():raise FileNotFoundError('Run python -m capdata fetch sta-layouts')
 if sha(f)!=expected[case[key]]['sha256']:raise ValueError('Physical input changed')
a.outdir.mkdir(parents=True,exist_ok=True)
result={}
for variant in ['golden']+[f'{m}_block{a.missing}_seed{s}' for s in range(3) for m in ['linear','ours']]:
 info=case['variants'][variant];spef=ROOT/info['spef']
 if sha(spef)!=info['spef_sha256']:raise ValueError('SPEF changed')
 out=a.outdir/variant;out.mkdir(exist_ok=False)
 env=dict(os.environ,STA_FLOW=str(a.flow.resolve()),STA_PLATFORM=platform,
          STA_LIBS=' '.join('{'+str((a.flow/n).resolve())+'}' for n in case['libraries']),
          STA_ODB=str(ROOT/case['odb']),STA_SDC=str(ROOT/case['sdc']),STA_SPEF=str(spef),STA_OUT=str(out.resolve()))
 log=out/'sta.log'
 with log.open('w') as f:subprocess.run([a.openroad,'-threads',str(a.threads),'-exit',str(ROOT/'analysis/sta/export.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 txt=log.read_text()
 if 'STA_EXPORT_COMPLETE' not in txt:raise RuntimeError(f'STA export failed: {log}')
 ws=float(re.search(r'worst slack max ([-.0-9]+)',txt)[1]);tns=float(re.search(r'tns max ([-.0-9]+)',txt)[1])
 for value,old,floor in [(ws,info['worst_slack_native'],1e-5),(tns,info['tns_native'],.01)]:
  if abs(value-old)>max(floor,abs(old)*1e-6):raise ValueError(f'Archived timing not reproduced: {variant}, {value}, {old}')
 result[variant]=dict(worst_slack_native=ws,tns_native=tns,spef_sha256=sha(spef))
 print(variant,'matches archived STA',flush=True)
(a.outdir/'verification.json').write_text(json.dumps(dict(case=a.case,variants=result,odb_sha256=sha(ROOT/case['odb']),sdc_sha256=sha(ROOT/case['sdc'])),indent=2)+'\n')
