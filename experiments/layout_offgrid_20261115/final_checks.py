import json,collections,hashlib,csv
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/layout_offgrid_20261115';OLD=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/pdkcap-v0/runs/reference_full_v2')
from pdkcap.solver import diagnose
controls=json.loads((O/'reference_plan_controls.json').read_text())['queries'];on=[]
for q in controls:
 rows=[]
 for lev in ['coarse','fine','wide']:
  p=O/'reference_results'/q['query_id']/lev;r=json.loads((p/'result.json').read_text());old=json.loads((OLD/(q['source_case']+'-'+lev)/'result.json').read_text())
  a,b=map(np.array,[r['matrix_F_per_m'],old['matrix_F_per_m']]);on.append(dict(query_id=q['query_id'],level=lev,relative_to_reused=float(np.linalg.norm(a-b)/np.linalg.norm(b)),bit_exact=bool(np.array_equal(a,b))))
  rows.append(dict(reference_id=q['query_id'],level=lev,status='completed',result=r))
 assert diagnose(rows)[0]['passed']
(O/'on_grid_alignment.json').write_text(json.dumps(on,indent=2))
# Read-only model provenance and explicit source-overlap checks.
import sys
sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
from common import tables,MODELS,PATHS,sha
provenance={}
for setting in ['public','to_asap7']:
 trained=tables(setting,'train');valid=tables(setting,'val')
 if setting=='to_asap7':assert all(t['process_id']=='freepdk15' for t in trained+valid)
 else:
  held={t['table_id'] for t in map(json.loads,(R/'runs/public_inventory_holdout_v1/tables.jsonl').read_text().splitlines()) if t['partition']=='holdout'}
  assert not held & {t['table_id'] for t in trained+valid}
  allpub=list(map(json.loads,(R/'runs/public_inventory_holdout_v1/tables.jsonl').read_text().splitlines()))
  def fingerprint(t):return hashlib.sha256(json.dumps([t['process_id'],t['family'],t['metal'],t['context_below'],t['context_above'],t['coordinates'],t['labels']],sort_keys=True).encode()).hexdigest()
  held_fingerprints={fingerprint(t) for t in allpub if t['partition']=='holdout'}
  assert not held_fingerprints & {fingerprint(t) for t in trained+valid}, 'duplicated target content in source'
  held_curves={h for t in allpub if t['partition']=='holdout' for h in t.get('curve_hashes',[])}
  assert not held_curves & {h for t in trained+valid for h in t.get('curve_hashes',[])}, 'duplicated source curves'
 checks={m:MODELS[setting]['checkpoints'] for m in ['full']}
 for m,folder in [('binary','binary'),('residual','residual')]:
  checks[m]=[dict(path=str(Path(PATHS['control_root'])/'runs'/f'{setting}_{folder}_s{s}'/'checkpoint.pt'),sha256=sha(Path(PATHS['control_root'])/'runs'/f'{setting}_{folder}_s{s}'/'checkpoint.pt')) for s in range(3)]
 sel=json.loads((R/f'results/dac_characterization_20261114/learning/{setting}_selection.json').read_text())
 for method,kind in [('mlp_adapt','mlp'),('cnp','cnp')]:
  lr=sel[kind]['lr'];checks[method]=[dict(path=str(R/f'results/dac_characterization_20261114/learning/{setting}_{kind}_lr{lr:g}_s{s}/checkpoint.pt'),sha256=sha(R/f'results/dac_characterization_20261114/learning/{setting}_{kind}_lr{lr:g}_s{s}/checkpoint.pt')) for s in range(3)]
 provenance[setting]=dict(methods=checks,source_train_ids=[t['table_id'] for t in trained],source_selection_ids=[t['table_id'] for t in valid],source_overlap_passed=True,duplicate_content_and_curve_check='passed for public held-out rules; FreePDK15-only source for ASAP7 templates',learning_selection=sel)
(O/'model_provenance.json').write_text(json.dumps(provenance,indent=2))
# Costs are deduplicated per batch; per-query copies are never summed.
cost=[]
for kind in ['native','fem']:
 rows=[json.loads(l) for l in (O/f'predictions_{kind}.jsonl').read_text().splitlines()];batches={}
 for r in rows:batches[r['batch_id'],r['method']]=r['batch_cost']
 for method in sorted(set(m for b,m in batches)):
  rr=[v for (b,m),v in batches.items() if m==method]
  cost.append(dict(stage=kind+'_prediction',method=method,batches=len(rr),cpu_s=sum(r['cpu_s'] for r in rr),wall_sum_s=sum(r['wall_s'] for r in rr),mean_batch_wall_ms=1000*np.mean([r['wall_s'] for r in rr]),scope='encoding/numerical branches/3 forwards; MLP includes fitting; model loading excluded'))
for p in sorted((O/'reference_results').glob('*/*/receipt.json')):
 r=json.loads(p.read_text());cost.append(dict(stage='reference',method=r['query_id']+':'+r['level'],batches=1,cpu_s=r['cpu_s'],wall_sum_s=r['wall_s'],mean_batch_wall_ms=1000*r['wall_s'],scope='single-thread process including setup; direct labels'))
for p in (O/'native').glob('*/*/receipt.json'):
 r=json.loads(p.read_text());cost.append(dict(stage='native_pex',method=r['case'],batches=2,cpu_s=r['cpu_s'],wall_sum_s=r['wall_s'],mean_batch_wall_ms=None,scope='original and instrumented extraction including DB load and SPEF; no new STA'))
r=json.loads((O/'build/receipt.json').read_text());cost.append(dict(stage='build',method='instrumented_openroad',batches=1,cpu_s=r['cpu_s'],wall_sum_s=r['wall_s'],mean_batch_wall_ms=None,scope='isolated compile/link children'))
with (O/'costs.csv').open('w') as f:w=csv.DictWriter(f,cost[0],lineterminator='\n');w.writeheader();w.writerows(cost)
# Native replay, direct FEM and unimplemented integrations are explicit.
summary=dict(native_census=True,native_electrical_parity_layouts=8,native_replay_queries=480,native_replay_reference='original evaluator; no physical accuracy interpretation',direct_FEM_formal_queries=71,direct_FEM_pilot_queries=12,on_grid_controls=12,extra_initial_control=1,reference_solves=len(list((O/'reference_results').glob('*/*/receipt.json'))),direct_FEM_mapping='LAYOUT_PARAMETERIZED_TEMPLATE',physically_aligned_native_reference_queries=0,exact_layout_sections=0,new_offline_rule_enrichment=False,in_extractor_replacement=False,existing_fixed_grid_rule_exports_preserved=True,measured_cpu_core_hours=sum(r['cpu_s'] for r in cost)/3600,cpu_accounting='measured solver/build/native/prediction stages; housekeeping, checks, failed preflights and partial scorer separately bounded by conservative reservation',conservative_total_core_hours_upper_bound=8,limitations=['Native trace covers specified getters only; no segment lengths/net IDs at this level','CTF and original native rules not physically aligned; independent native-vs-FEM accuracy comparison unavailable','No new enrichment or online replacement','New reference evidence covers one process, two layouts, idealized templates'])
assert summary['measured_cpu_core_hours']<8
(O/'COMPLETED.json').write_text(json.dumps(summary,indent=2));print(summary)
