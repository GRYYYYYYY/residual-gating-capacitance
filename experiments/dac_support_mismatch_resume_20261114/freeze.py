from core import *
from gates import prepare_gate
from paths import accounting
import subprocess,time
prepare_gate();assert all(len(verified_tables(s))==n for s,n in [('train',16),('val',24),('confirmation',16)])
# Reuse declared old S/Q, while independently verifying against the raw fixed trajectory records.
evals=json.loads((OLD/'EVALUATION_PLAN.json').read_text());assert len(evals)==256
raw=ROOT/'results/dac_characterization_20261114/confirmation_reference/records.jsonl.gz'
with gzip.open(raw,'rt') as f:oldrows=[json.loads(x) for x in f]
expected={(r['table_id'],r['data_seed'],r['budget']):(r['support_indices'],r['query_indices']) for r in oldrows if r['method']=='full' and r['strategy']=='farthest' and r['budget'] in [4,8,16,32]}
confirm={t['table_id']:t for t in verified_tables('confirmation')}
for e in evals:
 if e['cohort']=='low':assert (e['S'],e['Q'])==expected[e['table_id'],e['data_seed'],e['budget']]
 else:
  o,q=mask(confirm[e['table_id']]['coordinates'],e['protocol'],.3,11);assert e['S']==o.tolist() and e['Q']==q.tolist()
 assert not set(e['S'])&set(e['Q'])
write(OUT/'EVALUATION_PLAN.json',evals)
plan=json.loads((OLD/'FROZEN_PLAN.yaml').read_text());plan.update(attempt_id=ATTEMPT,start_sha=SETTINGS['start_sha'],freeze_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),failure='all endpoints required; NaN/Inf scientific stop; bounded ordinary engineering repairs allowed under 900 CPU seconds; no outcome-driven changes',prior_debit_cpu_seconds=SETTINGS['prior_debit_cpu_seconds'])
write(OUT/'FROZEN_PLAN.yaml',plan)
write(OUT/'RESOURCE_BUDGET.json',dict(hard_limit_cpu_s=14400,engineering_limit_cpu_s=900,prior_debit_cpu_s=SETTINGS['prior_debit_cpu_seconds'],prior_hashes=SETTINGS['prior_accounting_hashes'],new_admin_debit_cpu_s=30,pilot_updates_each=20,pilot_consumption='RESOURCE_LEDGER rows pilot_*; formal prefixes resume optimizer/RNG/step',feasibility='used cumulative CPU +2*max(pilot training CPU/20)*(24000-80)+1800 <=14400',measurement='single-thread/worker, waited process-tree RUSAGE_CHILDREN + supervisor SELF; prior60 not repeated; new30 explicitly conservative; /proc process-group watcher and RLIMIT_CPU'))
files=list(CODE.glob('*.py'))+[CODE/'ATTEMPT.json']+[OUT/n for n in ['PREPARE_SUCCESS.json','FROZEN_PLAN.yaml','RESOURCE_BUDGET.json','CHECKPOINT_LINEAGE.json','EPISODE_PLAN.json.gz','EVALUATION_PLAN.json','DATA_MANIFEST.json','EPISODE_PROVENANCE.json']]
files += [ROOT/'experiments/dac_characterization_20261114/common.py',ROOT/'experiments/dac_characterization_20261114/paths.json',ROOT/'configs/paper_models.json',ROOT/'experiments/paper_controls/run_controls.py']
# Actual imported Python implementation dependencies, plus frozen sampler/loss entrypoints.
for m in list(sys.modules.values()):
 p=getattr(m,'__file__',None)
 if p and str(p).endswith('.py'):
  p=Path(p).resolve()
  if p.is_relative_to(ROOT/'pdkcap') or p.is_relative_to(ROOT/'unified'):files.append(p)
for a in ['Full','binary']:
 for s in range(3):
  p=source(a,s);files += [p,p.parent/'FROZEN.json',p.parent/'COMPLETED.json']
# Keep source config/data origins and prior episode identity in the manifest.
files += [ROOT/source_config('reference',0)['data'],ROOT/MODELS['reference']['cohort'],ROOT/'runs/round3_validation_inputs_v1/reference_val.jsonl',OLD/'FROZEN_PLAN.yaml',OLD/'EPISODE_PLAN.json.gz',OLD/'EVALUATION_PLAN.json']
manifest={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in sorted(set(files))}
atomic_json(OUT/'FREEZE_MANIFEST.json',manifest)
atomic_json(OUT/'FREEZE_SUCCESS.json',dict(attempt_id=ATTEMPT,status='success',prepare_sha256=sha(OUT/'PREPARE_SUCCESS.json'),freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json'),source_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),actual_code_snapshot='manifest SHA256 of each executed dependency; working tree repair snapshot',artifacts={str((OUT/'FREEZE_MANIFEST.json').relative_to(ROOT)):sha(OUT/'FREEZE_MANIFEST.json')}))
print('FREEZE_SUCCESS',sha(OUT/'FREEZE_MANIFEST.json'),flush=True)
