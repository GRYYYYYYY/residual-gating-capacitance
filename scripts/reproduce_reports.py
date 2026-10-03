"""Reproduce historical v1.0.0 result tables, including STA results with --sta."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sta',action='store_true');p.add_argument('--output',type=Path,default=ROOT/'results/reproduced');a=p.parse_args()
a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
subprocess.run([sys.executable,str(ROOT/'analysis/build_tables.py'),'--regimes'],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(ROOT/'analysis/build_tables_v3.py')],cwd=ROOT,check=True)
expected=ROOT/'results/expected_tables';actual=ROOT/'analysis/tables';matched=[]
for f in expected.glob('*.tex'):
 if f.name=='sta_decision_fidelity.tex':continue
 candidate=actual/f.name
 if not candidate.is_file() or candidate.read_bytes()!=f.read_bytes():raise ValueError(f'Table mismatch: {f.name}')
 matched.append(f.name)
shutil.copytree(actual,a.output/'tables')
if a.sta:
 src=ROOT/'results/sta_visualization/gf180_ibex_50';dest=a.output/'sta'/'gf180_ibex_50'
 shutil.copytree(src/'raw',dest/'raw')
 shutil.copy2(src/'provenance.json',dest/'provenance.json')
 subprocess.run([sys.executable,str(ROOT/'analysis/sta/analyze_plot.py'),str(dest)],cwd=ROOT,check=True)
 if (a.output/'tables/sta_decision_fidelity.tex').read_bytes()!=(expected/'sta_decision_fidelity.tex').read_bytes():raise ValueError('STA table mismatch')
 matched.append('sta_decision_fidelity.tex')
(a.output/'verification.json').write_text(json.dumps(dict(matched_tables=matched,count=len(matched),status='passed'),indent=2)+'\n')
print('Verified',len(matched),'tables; recorded data reused, no model training.')
