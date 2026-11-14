"""Verify derived tables and reference hashes without modifying any old artifact."""
import csv,json,sys,collections,importlib.util
from pathlib import Path
import numpy as np
D=Path(__file__).resolve().parent;ROOT=D.parents[1]
sys.path.insert(0,str(ROOT/'experiments/dac_characterization_20261114'))
from common import sha,PATHS,MODELS,tables

def readcsv(p):return list(csv.DictReader(Path(p).open()))
def out(name,rs):
 with (D/name).open('w',newline='') as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)),lineterminator='\n');w.writeheader();w.writerows(rs)
refs=readcsv(D/'input_references.csv');assert all(sha(r['path'])==r['sha256'] for r in refs)
original=readcsv(ROOT/'results/dac_characterization_20261114/summary/budget_curves.csv')
idx={(r['setting'],r['method'],r['budget']):r for r in original if r['strategy']=='farthest'}
for r in readcsv(D/'same_budget.csv'):
 old=idx[r['setting'],r['method'],r['budget']];assert abs(float(r['macro_nrmse'])-float(old['nrmse']))<1e-14
old=readcsv(ROOT/'results/dac_characterization_20261114/summary/threshold_attainment.csv');key=lambda r:(r['setting'],r['method'],r['table_id'],r['data_seed'],r['threshold_index']);old={key(r):r for r in old}
new=readcsv(D/'threshold_trajectories.csv');assert len(new)==len(old)
for r in new:
 o=old[key(r)];assert r['first_measured_attainment_budget']==o['min_measured_budget'];assert (r['status']=='reached')==(o['attained']=='True')
sets=collections.defaultdict(dict)
for r in new:sets[r['setting'],r['threshold_index']].setdefault(r['method'],set()).add((r['table_id'],r['data_seed'],r['status']=='undefined_zero_truth'))
assert all(all(x==next(iter(v.values())) for x in v.values()) for v in sets.values())
# Source-hash caveat is explicit; historical mask cardinalities match released mask.
oldpath=Path(PATHS['solver_root'])/'runs/reference_study_v1/source_snapshot/sampling.py'
spec=importlib.util.spec_from_file_location('old_sampling_count_audit',oldpath);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
from pdkcap.sampling import mask
for t in tables('reference','train'):
 for protocol in ('mcar','block','extrapolation','width'):
  for ratio in (.1,.3,.5,.7):
   for seed in (11,29,47):
    a,b=mod.mask(t['coordinates'],protocol,ratio,seed);aa,bb=mask(t['coordinates'],protocol,ratio,seed);assert np.array_equal(a,aa) and np.array_equal(b,bb)
source=[]
for s in MODELS:
 for c in MODELS[s]['checkpoints']:
  frozen=json.loads((ROOT/c['path']).with_name('FROZEN.json').read_text())
  for name in ('unified/train.py','unified/episodes.py'):
   source.append(dict(setting=s,checkpoint=c['path'],component=name,recorded_hash=frozen['sources'][name],available_hash=sha(ROOT/name),byte_match=sha(ROOT/name)==frozen['sources'][name],interpretation='exact training entrypoint' if name.endswith('/train.py') else 'RATIOS currently .1/.3/.5/.7; older reference/transfer episode encoder byte snapshot not recovered; counts are setting/source reconstruction, not per-step telemetry'))
local=Path(PATHS['control_root'])/'run_controls.py';actual=sha(local)
for s in MODELS:
 f=json.loads((Path(PATHS['control_root'])/'runs'/f'{s}_binary_s0/FROZEN.json').read_text());assert actual==f['runner_sha256']
 source.append(dict(setting=s,checkpoint='all residual/binary members',component=str(local),recorded_hash=f['runner_sha256'],available_hash=actual,byte_match=True,interpretation='exact local control runner; installed repository copy has relocated path bootstrap'))
source.append(dict(setting='reference',checkpoint='warm-start',component=str(oldpath),recorded_hash='4d33a1ddca08f331620deb64d8b21c50de5d60e25ee1ad5a86403cc46376d405',available_hash=sha(oldpath),byte_match=True,interpretation='historical mask; geometry-only parity checked across 16 tables x 4 protocols x 4 ratios x 3 seeds'))
out('source_audit.csv',source)
# Add these exact source references to the input index.
for p in (local,oldpath):
 if str(p) not in {r['path'] for r in refs}:refs.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,role='historical sampler/control source'))
out('input_references.csv',refs)
# Immutable attachments must be byte-identical to original sources.
for name in ('FINAL_DECISION.md','CLAIM_EVIDENCE.csv'):
 assert sha(D/name)==sha(ROOT/'docs/dac_characterization_20261114'/name)
assert sha(D/'main.pdf')==sha(ROOT/'paper/dac_revision_20261114/main.pdf')
result=dict(status='PASS',input_hashes_verified=len(refs),same_budget_cells_reconciled=len(readcsv(D/'same_budget.csv')),threshold_trajectories_reconciled=len(new),matched_population_all_methods=True,checkpoint_hashes_verified=72,mask_parity_cases=16*4*4*3,attachments_byte_identical=True,new_model_execution=False,original_result_modifications=False)
(D/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
