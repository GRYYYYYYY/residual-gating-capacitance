"""Validate complete delivery and link local large artifacts without publishing."""
import json,gzip,collections,csv,subprocess,os
from common import *
R=ROOT/'results/dac_characterization_20261114';D=ROOT/'docs/dac_characterization_20261114'
checks={};all_rows=[]
for s in MODELS:
 folder=R/f'confirmation_{s}';frozen=json.loads((folder/'FROZEN.json').read_text());done=json.loads((folder/'COMPLETED.json').read_text());assert done['failed']==0 and done['records_sha256']==sha(folder/'records.jsonl.gz')
 rows=[json.loads(l) for l in gzip.open(folder/'records.jsonl.gz','rt')];assert len(rows)==done['records'];all_rows+=rows
 population={};keys=set()
 for r in rows:
  k=(r['table_id'],r['data_seed']);sig=(r['candidate_indices'],r['query_indices'])
  if k in population:assert population[k]==sig
  else:population[k]=sig
  assert not set(r['support_indices'])&set(r['query_indices']);assert set(r['support_indices'])<=set(r['candidate_indices'])
  assert len(set(r['history']))==r['budget']==r['support_count']==r['unique_reference_queries']
  key=(r['table_id'],r['data_seed'],r['strategy'],r['budget'],r['method']);assert key not in keys;keys.add(key)
  assert r['query_count']==len(r['query_indices'])==r['n'] and r['status']=='ok'
 checks[s]=dict(records=len(rows),table_seed_populations=len(population),no_failed_methods=True,identical_Q_across_all_budgets_methods_strategies=True)
 # Main comparison explicitly has all 12 methods on each eligible episode.
 primary=collections.defaultdict(set)
 for r in rows:
  if r['strategy']=='farthest':primary[r['table_id'],r['data_seed'],r['budget']].add(r['method'])
 assert all(v==set(json.loads((HERE/'EXPERIMENT_PLAN.yaml').read_text())['methods']) for v in primary.values())
for name in ('boundary_checks.json','learned_boundary_checks.json','geometry_cost_verification.json','export_batch_alignment.json','query_charge_verification.json'):assert (R/name).exists()
for name in ('boundary_checks.json','learned_boundary_checks.json'):
 for row in json.loads((R/name).read_text()):
  assert all(v for v in row.values() if isinstance(v,bool))
assert json.loads((R/'export_batch_alignment.json').read_text())['prediction_bit_exact']
assert json.loads((R/'summary/downstream_status.json').read_text())['complete']
native_manifest=json.loads((R/'summary/native_artifact_manifest.json').read_text())
for e in native_manifest['files']:assert sha(ROOT/e['path'])==e['sha256'],e['path']
checks['native_artifacts_verified']=len(native_manifest['files'])
for s in ('reference','to_asap7'):assert json.loads((R/f'attention/{s}_confirmation/COMPLETED.json').read_text())['failed']==0
assert (R/'reverse_transfer/COMPLETED.json').exists() and (R/'member_sensitivity/COMPLETED.json').exists()
# Published full members remain bit-identical, and original source HEAD/status unchanged.
for s in MODELS:
 for c in MODELS[s]['checkpoints']:assert sha(ROOT/c['path'])==c['sha256']
for c in json.loads((HERE/'MANIFEST.json').read_text())['controls']:assert sha(c['path'])==c['sha256']
checks['all_18_control_checkpoints_unchanged']=True
old=ROOT.parent/'residual-gating-capacitance';assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=old,text=True).strip()=='05d0717c31c3ebd38107c846cfa7712913078027'
assert subprocess.check_output(['git','status','--porcelain'],cwd=old,text=True)==''
# Small-artifact and local-binary hash index. Native files have a per-run manifest
# plus complete SPEF/input hashes already; do not repeatedly hash every ODB copy.
entries=[]
for folder in (HERE,D,R,ROOT/'paper/dac_revision_20261114'):
 for p in sorted(folder.rglob('*')):
  if not p.is_file() or 'downstream/native/' in str(p) or '__pycache__' in str(p) or p.name in ('DELIVERY_MANIFEST.json','FINAL_VERIFICATION.json'):continue
  if p.suffix in ('.aux','.log','.fls','.fdb_latexmk','.out'):continue
  entries.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)))
large=[e for e in entries if e['path'].endswith('.pt')]
checks['original_checkout_untouched']=True;checks['checkpoint_hashes_unchanged']=True;checks['local_binary_artifacts']=len(large)
checks['source_status']=subprocess.check_output(['git','status','--short'],text=True);checks['head']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
(D/'DELIVERY_MANIFEST.json').write_text(json.dumps(dict(files=entries,large_files_local_only=large,input_manifest_sha256=sha(HERE/'MANIFEST.json')),indent=2))
(D/'FINAL_VERIFICATION.json').write_text(json.dumps(checks,indent=2));print(checks)
