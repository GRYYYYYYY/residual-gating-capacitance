"""Bounded read-only polling; no weight loading or numerical analysis."""
from paths import *
import json
used,eng,rows=accounting();done=list((OUT/'checkpoints').glob('*/COMPLETED.json'))
print(json.dumps(dict(completed=len(done),units=[p.parent.name for p in done],cumulative_debit_s=used,engineering_debit_s=eng,remaining_closed_jobs_s=14400-used,failed_jobs=[r['job'] for r in rows if r['exit_code']]),ensure_ascii=False))
active=OUT/'ACTIVE.json'
if active.exists():
 a=json.loads(active.read_text());print(json.dumps(a));p=OUT/(a['job']+'.log')
 if p.exists():print('\n'.join(p.read_text().splitlines()[-2:]))
else:print('NO_ACTIVE_BUDGET_JOB')
