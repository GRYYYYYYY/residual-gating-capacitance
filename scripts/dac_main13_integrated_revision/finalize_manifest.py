"""Completion gate, provenance, original-input preservation and final file hashes."""
from pathlib import Path
import json,csv,hashlib,subprocess,sys,datetime,re
import difflib
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';D=R/'docs/dac_main13_integrated_revision';P=R/'paper/dac_layout_query_revision'
cache={}
def sha(p):
 p=Path(p)
 if str(p) not in cache:
  h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1048576),b''):h.update(b)
  cache[str(p)]=h.hexdigest()
 return cache[str(p)]
def js(p):return json.loads(Path(p).read_text())
def cmd(*args):return subprocess.check_output(args,cwd=R,text=True).strip()
receipts=['native/matrix_completed.json','native/smoke_pass.json','tests/final_contract_checks.json','tests/candidate_contract.json','tests/pdf_checks.json','post_native/completed.json','mechanism/candidate_scoring_completed.json','mechanism_diagnostic_checks.json','mli_status_reconciliation.json','coverage_trace_alignment.json']
for rel in receipts:assert js(O/rel)['status']=='PASS',rel
assert js(O/'tests/pdf_checks.json')['pdf_sha256']==sha(P/'main.pdf')
visual_path=O/'tests/pdf_visual_review.json'
visual_status='PASS' if visual_path.exists() and js(visual_path).get('status')=='PASS' and js(visual_path).get('pdf_sha256')==sha(P/'main.pdf') else 'NOT_RUN'
if visual_status=='PASS':receipts.append('tests/pdf_visual_review.json')
if not (O/'environment.json').exists():
 import numpy,scipy,torch
 (O/'environment.json').write_text(json.dumps(dict(python=sys.version,executable=sys.executable,numpy=numpy.__version__,scipy=scipy.__version__,torch=torch.__version__,torch_threads=torch.get_num_threads(),cuda_available=torch.cuda.is_available()),indent=2))
for domain in ['public','reference','to_asap7']:
 for stage in ['frozen','controls']:assert js(O/f'mechanism/{domain}_{stage}_completed.json')['episodes']=={'public':20400,'reference':960,'to_asap7':480}[domain]
assert max(js(O/'mechanism_replay_checks.json').values())<1e-7
queue=js(O/'controls/queue_completed.json');assert len(queue['tasks'])==18 and all(r.get('exit_code',0)==0 for r in queue['tasks'])
training=list(csv.DictReader((O/'training_opportunities.csv').open()));training=[r for r in training if r['method'] not in ['Binary','Ungated','C1 numerical gate','C3 no agreement']]
paths=js(R/'experiments/dac_characterization_20261114/paths.json');models=js(R/'configs/paper_models.json');new=[];source_inputs=set();initializers=[]
for domain in ['public','reference','to_asap7']:
 source_inputs.add(R/models[domain]['cohort'])
 for member,model in enumerate(models[domain]['checkpoints']):
  cfg=js((R/model['path']).parent/'FROZEN.json')['config'];p=R/cfg['init_from'];c=js(p.parent/'config.json');done=js(p.parent/'result.json');data=R/c['arguments']['data']
  released_data=data;metadata_difference=[]
  if sha(data)!=c['data_sha256']:
   data=Path(paths['solver_root'])/c['arguments']['data'];assert sha(data)==c['data_sha256']
   historical={t['table_id']:t for t in map(json.loads,data.read_text().splitlines())};released={t['table_id']:t for t in map(json.loads,released_data.read_text().splitlines())};assert historical.keys()==released.keys()
   metadata_difference=sorted({k for i in historical for k in historical[i].keys()|released[i].keys() if historical[i].get(k)!=released[i].get(k)});assert metadata_difference==['reference_contract']
  initializers.append(dict(domain=domain,member=member,checkpoint=str(p),checkpoint_sha256=sha(p),data=str(data),data_sha256=sha(data),released_copy=str(released_data),released_copy_sha256=sha(released_data),metadata_difference=json.dumps(metadata_difference),geometry_labels_partitions_equal=True,steps=c['arguments']['steps'],training_tables=c['training_tables'],validation_tables=c['validation_tables'],label_access=c['label_access'],wall_s=done['wall_seconds'],cpu_s=done.get('cpu_seconds','unmeasured'),scope='shared source residual initializer for Full/Binary/Ungated/C3; C1 uses scales/priors only and removes trunk; historical host timing, not newly benchmarked'))
  source_inputs.update([p,p.parent/'config.json',p.parent/'result.json',data,released_data])
 for variant,label,root in [('binary','Binary',Path(paths['control_root'])/'runs'),('residual','Ungated',Path(paths['control_root'])/'runs'),('numerical_gate','C1 numerical gate',O/'controls'),('no_agreement','C3 no agreement',O/'controls')]:
  for seed in range(3):
   folder=root/f'{domain}_{variant}_s{seed}';frozen=js(folder/'FROZEN.json');done=js(folder/'COMPLETED.json');cfg=frozen['config'];ck=folder/'checkpoint.pt';assert done['steps']==cfg['steps'] and sha(ck)==done['checkpoint_sha256']
   row=dict(domain=domain,method=label,member=seed,checkpoint=str(ck),checkpoint_sha256=sha(ck),steps=done['steps'],batch='one process-balanced episode per family/update',lr=cfg['learning_rate'],target_fit_steps=0,selection=frozen['selection'],source_config=str(folder/'FROZEN.json'),supervision='source-scaled component Huber; source fitting only',source_code_sha256=sha(R/'unified/train.py'),adapter_sha256=frozen['runner_sha256'],measured_final_stage_wall_s=done['wall_seconds'])
   training.append(row)
   if variant in ['numerical_gate','no_agreement']:new.append(dict(domain=domain,variant=variant,seed=seed,steps=done['steps'],wall_s=done['wall_seconds'],checkpoint_sha256=sha(ck),selection='frozen final-step recipe; no configuration grid or target selection',generic_training_receipt_status=done['status']))
   for name in ['data','scales_from','init_from']:
    if cfg.get(name):source_inputs.add(R/cfg[name])
   source_inputs.update([folder/'FROZEN.json',folder/'COMPLETED.json',ck])
for r in training:
 ck=Path(r['checkpoint']);source_inputs.add(ck);assert sha(ck)==r['checkpoint_sha256']
 f=ck.parent/'FROZEN.json';c=ck.parent/'COMPLETED.json'
 for p in [f,c]:
  if p.exists():source_inputs.add(p)
 if c.exists():r['measured_final_stage_wall_s']=js(c).get('wall_seconds','unmeasured')
 if r['method']=='Full' and not r.get('source_code_sha256'):r['source_code_sha256']=sha(R/'unified/train.py')
with (O/'training_opportunities.csv').open('w') as f:w=csv.DictWriter(f,list(dict.fromkeys(k for r in training for k in r)));w.writeheader();w.writerows(training)
with (O/'source_initializers.csv').open('w') as f:w=csv.DictWriter(f,list(initializers[0]));w.writeheader();w.writerows(initializers)
(O/'controls/evaluation_manifest.json').write_text(json.dumps(dict(status='PASS',members=new,total_final_stage_worker_seconds=sum(x['wall_s'] for x in new),queue_wall_s=queue['wall_s'],selection='single fixed recipe and final prescribed step; generic original trainer status does not imply unfinished hyperparameter selection'),indent=2))
# Reuse cryptographic preservation checks only while original file fingerprints match.
from verify_originals import verify
preservation=verify();preserved=preservation['snapshotted_sources_results_checked'];original_hashes=js(O/'original_input_hashes.json')
# Actual TeX dependency graph, repository implementation, source datasets/weights.
deps=set()
for line in (P/'main.fls').read_text().splitlines():
 if line.startswith('INPUT '):
  p=Path(line[6:]);p=p if p.is_absolute() else P/p;p=p.resolve()
  if p.is_file() and (p.is_relative_to(R) or p==R/'paper/IEEEtran.cls'):deps.add(p)
deps.update(source_inputs)
for folder in ['scripts/dac_main13_integrated_revision','configs/dac_main13_integrated_revision','unified','pdkcap','experiments/paper_controls','experiments/dac_characterization_20261114','experiments/pex_kernel_revision']:
 for p in (R/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.sh','.json','.yaml','.gz','.csv','.tcl']:deps.add(p)
for p in [P/'main.tex',P/'main.pdf',P/'main.bbl',P/'references.bib',R/'configs/paper_models.json',R/'CODEX_DAC_CAPACITANCE_MAIN13_INTEGRATED_REVISION.md']:deps.add(p)
for p in D.iterdir():
 if p.is_file() and p.suffix in ['.md','.csv','.json']:deps.add(p)
for r in js(O/'coverage_checks.json')['sources']:deps.add(R/r)
snapshot=Path(js(D/'snapshot.json')['path']);patch=[]
for p in sorted(deps):
 if p.suffix!='.tex' or not p.is_relative_to(P):continue
 old=snapshot/p.relative_to(R)
 before=old.read_text().splitlines(keepends=True) if old.exists() else []
 after=p.read_text().splitlines(keepends=True)
 if before!=after:patch.extend(difflib.unified_diff(before,after,fromfile='main13/'+str(p.relative_to(R)),tofile='revision/'+str(p.relative_to(R))))
review=D/'revision_from_main13.patch';review.write_text(''.join(patch));deps.add(review)
dep_hashes={str(p):sha(p) for p in sorted(deps)};(O/'dependency_manifest.json').write_text(json.dumps(dep_hashes,indent=2))
(O/'original_input_hashes.json').write_text(json.dumps(original_hashes,indent=2))
# Logs must show successful compilation; page count is not an acceptance criterion.
log=(P/'main.log').read_text();assert 'Output written on main.pdf' in log
assert not re.search(r'Overfull|undefined references|Citation .* undefined|Missing character',log)
out_hashes={str(p.relative_to(R)):sha(p) for p in O.rglob('*') if p.is_file() and p.name!='manifest.json'}
manifest=dict(experiment_id=O.name,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),repository=str(R),branch=cmd('git','branch','--show-current'),head=cmd('git','rev-parse','HEAD'),worktree='original requested workspace on dedicated revision branch; dirty changes preserved',committed=False,pushed=False,source=str(P/'main.tex'),pdf=str(P/'main.pdf'),pdf_sha256=sha(P/'main.pdf'),environment=js(O/'environment.json'),openroad_commit='0b54bb3203e0895f87940ff982358a6e4d406e28',status=dict(pdf_visual_review=visual_status,implementation='PASS',experiments='PASS',offline_consistency_point_estimate='PASS',statistical_no_regression_guarantee='INCONCLUSIVE',universal_sparse_native_improvement='FAIL',equal_accuracy_end_to_end_speedup='NOT_RUN'),completion_receipts=receipts,outputs=out_hashes,dependencies='dependency_manifest.json',preservation='tests/original_preservation.json',reproduction='scripts/dac_main13_integrated_revision/reproduce.sh',limitations=['post-hoc default and mechanism analysis','only4 FEM/2 transfer groups;4 native process clusters','full-rule native reference is output fidelity, not physical truth','Q-conditioned outputs under frozen canonical batching','source label generation/full historical training/paid target acquisition unmeasured','new native time is shared-host stage timing; cold/reuse totals modeled'])
(O/'manifest.json').write_text(json.dumps(manifest,indent=2));print('FINAL_MANIFEST_PASS',len(out_hashes),'outputs',len(dep_hashes),'dependencies',preserved,'preserved files')
