"""Lightweight audit/packaging; covered by the explicit 60s administration debit."""
import json,csv,hashlib,zipfile,time,subprocess,os,shutil
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'results/dac_support_mismatch_20261114';D=ROOT/'docs/dac_support_mismatch_20261114';P=ROOT/'paper/dac_support_revision_20261114';REVIEW=ROOT/'review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
assert not (R/'ACTIVE.json').exists()
assert not (R/'FREEZE_MANIFEST.json').exists()
assert not (R/'checkpoints').exists()
rows=[json.loads(l) for l in (R/'RESOURCE_LEDGER.jsonl').read_text().splitlines()]
assert len(rows)==5 and [r['exit_code'] for r in rows]==[1,1,1,0,0]
with (R/'RESOURCE_LEDGER.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
measured=sum(r['child_user_cpu_s']+r['child_system_cpu_s']+r['supervisor_cpu_s'] for r in rows);charged=sum(r['charged_cpu_seconds'] for r in rows)
summary=dict(measured_cpu_seconds=measured,measured_cpu_core_hours=measured/3600,administrative_conservative_charge_s=60,charged_cpu_seconds=charged,charged_cpu_core_hours=charged/3600,hard_limit_cpu_s=14400,remaining_charged_cpu_s=14400-charged,worker_wall_sum_s=sum(r['wall_seconds'] for r in rows),measured_stage_start_utc=rows[0]['start_utc'],measured_stage_end_utc=rows[-1]['end_utc'],measured_stage_elapsed_wall_s=(datetime.fromisoformat(rows[-1]['end_utc'].replace('Z','+00:00'))-datetime.fromisoformat(rows[0]['start_utc'].replace('Z','+00:00'))).total_seconds(),delivery_snapshot_utc=datetime.now(timezone.utc).isoformat(),training_cpu_s=0,pilot_cpu_s=0,formal_prediction_cpu_s=0,threads=1,max_concurrency=1,gpu_jobs=0,solver_jobs=0,PEX_STA_jobs=0,stage_note='measured phase wall includes between-stage drafting; initial read-only audit and final git/publication are outside this wall definition; their lightweight administration has conservative CPU debit, not invented measurement')
dump(R/'RESOURCE_SUMMARY.json',summary)
report=(D/'MECHANISM_REPORT.md').read_text();report+=f'''\n## 最终计量快照\n\n实测子进程树及监督CPU共 **{measured:.6f}秒（{measured/3600:.6f} core-hours）**；另计60秒行政保守费用，总预算扣账 **{charged:.6f}秒（{charged/3600:.6f} core-hours）**，距14,400秒硬限剩余{14400-charged:.6f}秒。五个被监督工作进程墙钟合计{summary['worker_wall_sum_s']:.3f}秒；首个计量阶段启动至最后阶段退出为{summary['measured_stage_elapsed_wall_s']:.0f}秒（包含中间文稿编写间隔，不含最初只读审计及最终Git传输）。正式训练/pilot/终点评测均为零。\n''';(D/'MECHANISM_REPORT.md').write_text(report)
# Verify old tracked artifacts remained unchanged, not just the old paper snapshot.
changed=subprocess.check_output(['git','diff','--name-only','b0a2edcac216af53b417be2a3b922c4deff98185'],cwd=ROOT,text=True).splitlines();assert changed==['.gitignore'],changed
manifest=json.loads((R/'PAPER_PROVENANCE.json').read_text());assert sha(Path(manifest['original_pdf_path']))==manifest['original_pdf_sha256']
newtex=(P/'main.tex').read_text();assert 'No continuation endpoint or matched endpoint evaluation was completed.' in newtex
pdftxt=subprocess.check_output(['pdftotext',str(P/'main.pdf'),'-'],text=True);assert 'No continuation endpoint or matched endpoint evaluation was' in pdftxt
assert len(list(csv.DictReader((R/'ENDPOINT_STATUS.csv').open())))==12
assert len(list(csv.DictReader((R/'EVALUATION_CELLS.csv').open())))==0
assert len(json.loads((R/'EVALUATION_PLAN.json').read_text()))==256
# Six source-weight hashes checked again; reads only, no new model inference.
for row in csv.DictReader((R/'SOURCE_WEIGHT_MANIFEST.csv').open()):assert sha(Path(row['path']))==row['sha256']
oldreview=ROOT/'review/dac_capacitance_20261114'
files=list(D.glob('*'))+[p for p in R.rglob('*') if p.is_file() and p.name!='budget.lock']+[P/'main.pdf',P/'main.tex',P/'DAC_REWRITE.md',P/'REVISION_NOTES.md']+list((P/'figures').glob('*.pdf'))+list(Path(__file__).parent.glob('*.py'))
files += [oldreview/'REVIEW_PACKET.md',oldreview/'FINAL_DECISION.md',oldreview/'CLAIM_EVIDENCE.csv']+list(oldreview.glob('*.csv'))
files=sorted(set(p for p in files if p.is_file()),key=lambda p:str(p.relative_to(ROOT)))
# Package old review tables as preserved evidence, not newly collected measurements.
manifest_text=''.join(f'{sha(p)}  {p.relative_to(ROOT)}\n' for p in files)
archive=REVIEW/'DAC_SUPPORT_MISMATCH_20261114.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files:z.write(p,p.relative_to(ROOT))
 z.writestr('SHA256SUMS',manifest_text)
 z.writestr('README.txt','Mechanism status: INCONCLUSIVE_IMPLEMENTATION. Global: COMPLETION_ACCURACY_ONLY. 0/12 endpoints completed; no C/D/I/G measured. Start commit b0a2edcac216af53b417be2a3b922c4deff98185. Plans are incomplete freeze-attempt artifacts. See docs/dac_support_mismatch_20261114/MECHANISM_REPORT.md first. Original REVIEW_PACKET and decision are unchanged historical records. Large source weights are only path/hash references. Final delivery commit is the Git commit containing this archive, also reported outside it.\n')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for l in z.read('SHA256SUMS').decode().splitlines():h,p=l.split('  ',1);assert hashlib.sha256(z.read(p)).hexdigest()==h
(REVIEW/'DAC_SUPPORT_MISMATCH_20261114.sha256').write_text(f'{sha(archive)}  {archive.name}\n')
(REVIEW/'DAC_SUPPORT_MISMATCH_20261114_FILES.sha256').write_text(manifest_text)
dump(R/'DELIVERY_VERIFICATION.json',dict(archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,archive_entries=len(files)+2,all_member_hashes_verified=True,old_tracked_artifacts_unchanged=True,six_source_weights_rehashed=True,pdf_text_verified=True,no_active_budget_job=True,freeze_incomplete_intentionally=True,no_new_checkpoints=True))
print(json.dumps(summary,indent=2));print('ARCHIVE',str(archive),archive.stat().st_size,sha(archive))
