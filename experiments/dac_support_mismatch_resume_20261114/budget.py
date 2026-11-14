"""Single owner with cumulative and engineering sub-budget enforcement."""
import os,sys,json,time,resource,subprocess,signal,fcntl
from pathlib import Path
from paths import *
OUT.mkdir(exist_ok=True);lock=open(OUT/'budget.lock','a');fcntl.flock(lock,fcntl.LOCK_EX)
used,engineering,rows=accounting();phase,name=sys.argv[1:3];command=sys.argv[3:]
assert phase in ['engineering','pilot','training','evaluation','analysis','delivery']
admin=SETTINGS['new_administrative_debit_seconds'] if not rows else 0
remaining=SETTINGS['hard_limit_cpu_seconds']-used-admin-30
if phase=='engineering':remaining=min(remaining,SETTINGS['engineering_limit_cpu_seconds']-engineering-admin-5)
if remaining<1:raise SystemExit('INCONCLUSIVE_BUDGET')
log=OUT/(name+'.log');assert not log.exists(),'immutable job name'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
def limit():resource.setrlimit(resource.RLIMIT_CPU,(int(remaining),int(remaining)+1))
start=time.time();started=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());killed=False
with log.open('x') as out:
 p=subprocess.Popen(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limit)
 atomic_json(OUT/'ACTIVE.json',dict(attempt_id=ATTEMPT,job=name,phase=phase,pid=p.pid,start_utc=started,cumulative_prior_cpu_s=used,cpu_remaining=remaining))
 while p.poll() is None:
  cpu=0.
  for f in Path('/proc').glob('[0-9]*/stat'):
   try:
    v=f.read_text().rsplit(')',1)[1].split()
    if int(v[2])==p.pid:cpu+=sum(float(v[i]) for i in (11,12,13,14))/os.sysconf('SC_CLK_TCK')
   except (OSError,ValueError,IndexError):pass
  me=resource.getrusage(resource.RUSAGE_SELF)
  if cpu+me.ru_utime+me.ru_stime>=remaining or time.time()-start>10800:
   os.killpg(p.pid,signal.SIGKILL);killed=True;break
  time.sleep(1)
 rc=p.wait()
ch=resource.getrusage(resource.RUSAGE_CHILDREN);me=resource.getrusage(resource.RUSAGE_SELF)
row=dict(attempt_id=ATTEMPT,phase=phase,job=name,command=command,start_utc=started,end_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),wall_seconds=time.time()-start,child_user_cpu_s=ch.ru_utime,child_system_cpu_s=ch.ru_stime,supervisor_cpu_s=me.ru_utime+me.ru_stime,administrative_conservative_charge_s=admin,charged_cpu_seconds=ch.ru_utime+ch.ru_stime+me.ru_utime+me.ru_stime+admin,exit_code=rc,budget_kill=killed,threads=1,concurrency=1,maxrss_kib=ch.ru_maxrss,cumulative_debit_before_s=used)
with (OUT/'RESOURCE_LEDGER.jsonl').open('a') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
(OUT/'ACTIVE.json').unlink();print(json.dumps(row),flush=True)
raise SystemExit(rc if rc>=0 else 1)
