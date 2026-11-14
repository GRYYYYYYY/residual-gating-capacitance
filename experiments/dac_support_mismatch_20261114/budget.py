"""Single-owner CPU budget supervisor. All scientific subprocesses go here."""
import os,sys,json,time,resource,subprocess,signal,fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'results/dac_support_mismatch_20261114'
OUT.mkdir(exist_ok=True); lock=open(OUT/'budget.lock','a');fcntl.flock(lock,fcntl.LOCK_EX)
ledger=OUT/'RESOURCE_LEDGER.jsonl'
rows=[json.loads(s) for s in ledger.read_text().splitlines()] if ledger.exists() else []
used=sum(r['charged_cpu_seconds'] for r in rows)
# 60 seconds charged once for prior shell-only audit, configuration and unmetered administration.
admin=60 if not rows else 0
remaining=14400-used-admin-30
if remaining<1:raise SystemExit('INCONCLUSIVE_BUDGET: no CPU allocation remains')
name=sys.argv[1];command=sys.argv[2:];log=OUT/(name+'.log')
assert not log.exists(), 'job names immutable'
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
def limit():resource.setrlimit(resource.RLIMIT_CPU,(int(remaining),int(remaining)+1))
start=time.time();started=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());timed=False
with log.open('x') as out:
 p=subprocess.Popen(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limit)
 (OUT/'ACTIVE.json').write_text(json.dumps(dict(job=name,pid=p.pid,start_utc=started,cpu_remaining=remaining)))
 while p.poll() is None:
  # CPU process group includes each live process's own ticks plus reaped-child ticks.
  cpu=0
  for f in Path('/proc').glob('[0-9]*/stat'):
   try:
    v=f.read_text().rsplit(')',1)[1].split()
    if int(v[2])==p.pid:cpu+=sum(float(v[i]) for i in (11,12,13,14))/os.sysconf('SC_CLK_TCK')
   except (OSError,ValueError,IndexError):pass
  if cpu+resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime>=remaining or time.time()-start>10800:
   timed=True;os.killpg(p.pid,signal.SIGKILL);break
  time.sleep(1)
 rc=p.wait()
ch=resource.getrusage(resource.RUSAGE_CHILDREN);me=resource.getrusage(resource.RUSAGE_SELF)
row=dict(job=name,command=command,start_utc=started,end_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),wall_seconds=time.time()-start,child_user_cpu_s=ch.ru_utime,child_system_cpu_s=ch.ru_stime,supervisor_cpu_s=me.ru_utime+me.ru_stime,administrative_conservative_charge_s=admin,charged_cpu_seconds=ch.ru_utime+ch.ru_stime+me.ru_utime+me.ru_stime+admin,exit_code=rc,budget_kill=timed,threads=1,concurrency=1,maxrss_kib=ch.ru_maxrss)
with ledger.open('a') as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
(OUT/'ACTIVE.json').unlink(missing_ok=True)
print(json.dumps(row),flush=True)
raise SystemExit(rc if rc>=0 else 1)
