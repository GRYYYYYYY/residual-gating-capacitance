"""Case-disjoint native scheduler. Never use while serial downstream.py is live."""
import concurrent.futures,subprocess,sys,json,time,os,fcntl
from common import ROOT,HERE,write
from downstream import R,CASES
D=R/'parallel_queue';D.mkdir(exist_ok=False)
lock=(R/'queue.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
write(D/'FROZEN.json',dict(max_concurrency=2,pid=os.getpid(),cases=list(CASES),scope='one worker owns each entire fixed-layout case; existing completed receipts reused'))
def run(case):
 cmd=[sys.executable,str(HERE/'downstream.py'),'--case',case];start=time.perf_counter()
 with (D/(case.replace('/','_')+'.log')).open('x') as f:
  try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=7200);rc=r.returncode
  except subprocess.TimeoutExpired:rc=None
 result=dict(case=case,exit_code=rc,wall_seconds=time.perf_counter()-start);write(D/(case.replace('/','_')+'.json'),result);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES))
write(D/'COMPLETED.json',dict(results=results));print(results,flush=True)
