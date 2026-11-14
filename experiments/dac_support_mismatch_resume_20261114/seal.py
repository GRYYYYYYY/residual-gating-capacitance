"""Light administrative sealing, covered by the new30s debit; no scientific compute."""
import json,csv,hashlib,zipfile,subprocess
from datetime import datetime,timezone
from paths import *
assert not (OUT/'ACTIVE.json').exists()
assert (OUT/'DELIVERY_VERIFICATION.json').exists()
used,eng,rows=accounting();oldrows=[json.loads(l) for l in (OLD/'RESOURCE_LEDGER.jsonl').read_text().splitlines()]
assert used<14400 and eng<900
measured=sum(r['child_user_cpu_s']+r['child_system_cpu_s']+r['supervisor_cpu_s'] for r in rows);new=sum(r['charged_cpu_seconds'] for r in rows);old=json.loads((OLD/'RESOURCE_SUMMARY.json').read_text())
fields=list(rows[0]);
with (OUT/'RESOURCE_LEDGER.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
summary=dict(prior_debit_cpu_seconds=SETTINGS['prior_debit_cpu_seconds'],prior_measured_cpu_seconds=old['measured_cpu_seconds'],prior_conservative_debit_s=60,new_measured_cpu_seconds=measured,new_conservative_debit_s=30,new_charged_cpu_seconds=new,cumulative_measured_cpu_seconds=old['measured_cpu_seconds']+measured,cumulative_charged_cpu_seconds=used,cumulative_charged_core_hours=used/3600,hard_limit_cpu_seconds=14400,remaining_cpu_seconds=14400-used,engineering_debit_cpu_seconds=eng,engineering_limit_cpu_seconds=900,new_worker_wall_sum_s=sum(r['wall_seconds'] for r in rows),new_phase_start_utc=rows[0]['start_utc'],new_phase_end_utc=rows[-1]['end_utc'],new_phase_elapsed_wall_s=(datetime.fromisoformat(rows[-1]['end_utc'].replace('Z','+00:00'))-datetime.fromisoformat(rows[0]['start_utc'].replace('Z','+00:00'))).total_seconds(),threads=1,concurrency=1,endpoints_completed=12,endpoints_failed=0,stage_failures=sum(r['exit_code']!=0 for r in rows),note='Final lightweight sealing and git/publication administration covered by new30s conservative debit; not reported as measured CPU. Prior60 included once, new30 distinct. Driver waits for every child; descendant CPU not double counted.')
(OUT/'RESOURCE_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
with (DOC/'MECHANISM_REPORT.md').open('a') as f:f.write(f'''\n## 最终累计计量\n\n旧扣账{SETTINGS['prior_debit_cpu_seconds']:.6f}秒；本次实测{measured:.6f}秒，另列本次30秒行政保守费用，本次扣账{new:.6f}秒；累计扣账 **{used:.6f}秒（{used/3600:.6f} CPU core-hours）**，原14,400秒上限剩余{14400-used:.6f}秒。累计实测{old['measured_cpu_seconds']+measured:.6f}秒；旧60秒与新30秒保守费用分开，未重复扣旧费。工程阶段{eng:.6f}/900秒。本次工作进程墙钟合计{summary['new_worker_wall_sum_s']:.3f}秒，首个计量阶段至最后阶段退出跨度{summary['new_phase_elapsed_wall_s']:.0f}秒。阶段失败{summary['stage_failures']}，12终点均完成；旧两次预检和依赖冻结失败记录仍保留，不改写为成功。\n''')
claims=[['R1','Exact paired low-support protocol under unchanged scientific parameters','SUPPORTED_EXECUTION','FROZEN_PLAN.yaml; EPISODE_PROVENANCE.json; PREPARE_SUCCESS.json'],['R2','C/D/I/G and per-seed consistency','MEASURED_LOCAL','EFFECTS_BY_SEED.csv; EFFECT_SUMMARY.csv; EFFECTS_BY_SEED_BUDGET.csv'],['R3','Independent confirmation, pure cardinality causality or global architecture necessity','NOT_ESTABLISHED','MECHANISM_REPORT.md: retrospective four-group scope and induced coverage change'],['R4','New solver, transfer, native PEX/STA or whole-process efficiency gains','NOT_MEASURED','RESOURCE_LEDGER.csv; scope; original FINAL_DECISION unchanged'],['R5','Global COMPLETION_ACCURACY_ONLY','UNCHANGED','FINAL_DECISION.md']]
with (DOC/'CLAIM_EVIDENCE.csv').open('w',newline='') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow(['claim_id','claim','status','evidence']);w.writerows(claims)
# Source6 and final12 weights are referenced, not included; raw prediction arrays likewise.
files=list(DOC.glob('*'))+[q for q in OUT.rglob('*') if q.is_file() and q.suffix!='.pt' and q.name not in ['budget.lock','PREDICTIONS.jsonl.gz','driver.log']]+list(CODE.glob('*.py'))+[CODE/'ATTEMPT.json']
paper=ROOT/json.loads((OUT/'PAPER_FINAL_SUCCESS.json').read_text())['paper'];files += [paper/n for n in ['DAC_REWRITE.md','main.tex','main.pdf','SOURCE_OF_TRUTH.md']]+list((paper/'figures').glob('*.pdf'))
files += [ROOT/'review/dac_capacitance_20261114/REVIEW_PACKET.md',OLD/'RESOURCE_SUMMARY.json',ROOT/'docs/dac_support_mismatch_20261114/MECHANISM_REPORT.md',ROOT/'docs/dac_characterization_20261114/FINAL_DECISION.md',ROOT/'docs/dac_characterization_20261114/CLAIM_EVIDENCE.csv']
files=sorted(set(q for q in files if q.is_file()),key=lambda q:str(q.relative_to(ROOT)))
manifest=''.join(f'{sha(q)}  {q.relative_to(ROOT)}\n' for q in files);archive=ROOT/'review/DAC_MECHANISM_RESUME_20261114.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for q in files:z.write(q,q.relative_to(ROOT))
 z.writestr('SHA256SUMS',manifest);z.writestr('README.txt','Start with docs/dac_support_mismatch_resume_20261114/MECHANISM_REPORT.md. Twelve fixed2000-update endpoints completed. Old failure record included as historical evidence. Global COMPLETION_ACCURACY_ONLY unchanged. Source/final weights and raw predictions remain path/hash references; see LARGE_ARTIFACTS.csv and CHECKPOINT_LINEAGE.json. The Git commit containing this archive is the delivery commit, reported outside the archive to avoid a circular self-reference.\n')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for line in z.read('SHA256SUMS').decode().splitlines():h,p=line.split('  ',1);assert hashlib.sha256(z.read(p)).hexdigest()==h
(archive.with_suffix('.sha256')).write_text(f'{sha(archive)}  {archive.name}\n')
(ROOT/'review/DAC_MECHANISM_RESUME_20261114_FILES.sha256').write_text(manifest)
print(json.dumps(summary,indent=2));print('ARCHIVE',archive,archive.stat().st_size,sha(archive))
