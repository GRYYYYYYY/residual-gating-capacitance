from core import *
from paths import accounting
import time
plan=check_frozen();pilots=[];artifacts={}
for a in ['Full','binary']:
 for arm in ['H','L']:
  unit=f'{a}_{arm}_s0';p=OUT/'checkpoints'/unit/'PILOT.json';r=json.loads(p.read_text());resume=OUT/'resume'/f'{unit}.pt'
  assert r['status']=='success' and r['attempt_id']==ATTEMPT and r['freeze_sha256']==sha(OUT/'FREEZE_MANIFEST.json') and r['updates']==20 and r['startstep']==0 and r['resume_sha256']==sha(resume)
  pilots.append(r);artifacts[str(p.relative_to(ROOT))]=sha(p);artifacts[str(resume.relative_to(ROOT))]=sha(resume)
used,eng,ledger=accounting();slow=max(p['training_cpu_s']/20 for p in pilots);estimate=used+time.process_time()+30+2*slow*(24000-80)+1800
result=dict(attempt_id=ATTEMPT,freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json'),cumulative_debit_before_stage_s=used,current_stage_measured_so_far_s=time.process_time(),current_stage_safety_allowance_s=30,engineering_used_s=eng,max_pilot_cpu_per_update=slow,pilot_summaries=pilots,remaining_updates=23920,safety_factor=2,prediction_statistics_exit_reserve_s=1800,estimated_total_cpu_s=estimate,cap_cpu_s=14400,pass_feasibility=bool(estimate<=14400))
write(OUT/'FEASIBILITY.json',result)
if estimate>14400:raise SystemExit('INCONCLUSIVE_BUDGET: do not reduce updates or omit controls')
artifacts[str((OUT/'FEASIBILITY.json').relative_to(ROOT))]=sha(OUT/'FEASIBILITY.json')
atomic_json(OUT/'FEASIBILITY_PASS.json',dict(status='success',attempt_id=ATTEMPT,freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json'),artifacts=artifacts))
print('FEASIBILITY_PASS',estimate,'/',14400,flush=True)
