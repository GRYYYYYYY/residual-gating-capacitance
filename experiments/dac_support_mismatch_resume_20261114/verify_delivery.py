"""Independent arithmetic/provenance and final artifact checks; no new inference."""
import csv,json,math,subprocess,hashlib
from collections import defaultdict
from paths import *
from gates import endpoint_gate
plan=endpoint_gate();assert (OUT/'ANALYSIS_SUCCESS.json').exists() and (OUT/'PAPER_FINAL_SUCCESS.json').exists()
# Recompute the primary without pandas, respecting each declared aggregation level.
raw=list(csv.DictReader((OUT/'EVALUATION_CELLS.csv').open()));cells=defaultdict(list)
for r in raw:
 if r['cohort']!='low' or float(r['squared_truth'])<=0:continue
 key=(r['architecture'],r['arm'],int(r['train_seed']),int(r['budget']),r['group'],r['table_id'],int(r['data_seed']))
 cells[key].append(math.sqrt(float(r['squared_error'])/float(r['squared_truth'])))
def collapse(d):
 out=defaultdict(list)
 for k,vs in d.items():out[k[:-1]].append(sum(vs)/len(vs))
 return out
# Components -> data seeds -> tables -> groups -> four budgets.
bytable=collapse(cells);bygroup=collapse(bytable);bybudget=collapse(bygroup);byseed=collapse(bybudget)
primary={k:sum(v)/len(v) for k,v in byseed.items()}
for r in csv.DictReader((OUT/'EFFECTS_BY_SEED.csv').open()):
 s=int(r['train_seed']);e={f'E_{a}_{arm}':primary[a,arm,s] for a in ['Full','binary'] for arm in ['0','H','L']}
 e.update(C_Full=e['E_Full_0']-e['E_Full_H'],C_binary=e['E_binary_0']-e['E_binary_H'],D_Full=e['E_Full_H']-e['E_Full_L'],D_binary=e['E_binary_H']-e['E_binary_L']);e.update(I=e['D_Full']-e['D_binary'],G=e['E_binary_L']-e['E_Full_L'])
 for k,v in e.items():assert math.isclose(v,float(r[k]),rel_tol=1e-12,abs_tol=1e-14),(k,s,v,r[k])
assert len(raw)==13824
for r in json.loads((OUT/'CHECKPOINT_LINEAGE.json').read_text()):assert sha(r['path'])==r['sha256']
assert sha(CODE/'analyze.py')==(OUT/'ANALYSIS_CODE_BEFORE_EVALUATION.sha256').read_text().split()[0]
paper=json.loads((OUT/'PAPER_FINAL_SUCCESS.json').read_text());p=ROOT/paper['paper']
for n,key in [('DAC_REWRITE.md','markdown_sha256'),('main.tex','tex_sha256'),('main.pdf','pdf_sha256')]:assert sha(p/n)==paper[key]
# Re-render in memory elsewhere is unnecessary; regenerate identical TeX and compare hash.
subprocess.run([__import__('sys').executable,str(CODE/'render_paper.py'),str(p)],check=True);assert sha(p/'main.tex')==paper['tex_sha256']
changed=subprocess.check_output(['git','diff','--name-only',SETTINGS['start_sha']],cwd=ROOT,text=True).splitlines();assert changed==['.gitignore'],changed
weights=[]
for q in sorted((OUT/'checkpoints').glob('*/checkpoint.pt')):weights.append(dict(kind='final_weight',path=str(q),sha256=sha(q),bytes=q.stat().st_size))
for q in sorted((OUT/'resume').glob('*.pt')):weights.append(dict(kind='pilot_resume',path=str(q),sha256=sha(q),bytes=q.stat().st_size))
q=OUT/'PREDICTIONS.jsonl.gz';weights.append(dict(kind='raw_predictions',path=str(q),sha256=sha(q),bytes=q.stat().st_size))
with (OUT/'LARGE_ARTIFACTS.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['kind','path','sha256','bytes'],lineterminator='\n');w.writeheader();w.writerows(weights)
atomic_json(OUT/'DELIVERY_VERIFICATION.json',dict(attempt_id=ATTEMPT,status='success',independent_primary_arithmetic=True,all12_checkpoints_verified=True,old_tracked_artifacts_unchanged=True,analysis_code_bound_before_evaluation=True,markdown_tex_roundtrip_identical=True,raw_component_rows=13824,freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json')))
import importlib.metadata,sys,platform
atomic_json(OUT/'ENVIRONMENT.json',dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['torch','numpy','scipy','pandas','matplotlib']},threads=1,workers=1,gpu=False))
print('FINAL_VERIFICATION_PASS',flush=True)
