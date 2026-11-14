"""One owner, strict success dependencies. No automatic failed-run retries."""
import subprocess,sys,json,time
from paths import *

def run_chain(commands):
 for command in commands:subprocess.run(command,cwd=ROOT,check=True)

def main():
 def job(phase,name,script,*args):return [sys.executable,str(CODE/'budget.py'),phase,name,sys.executable,str(CODE/script),*args]
 commands=[job('engineering','regression','regression.py'),job('engineering','prepare','prepare.py'),job('engineering','freeze','freeze.py')]
 commands += [job('pilot',f'pilot_{a}_{arm}_s0','worker.py',a,arm,'0','--pilot') for a in ['Full','binary'] for arm in ['H','L']]
 commands += [job('pilot','feasibility','feasibility.py')]
 commands += [job('training',f'final_{a}_{arm}_s{s}','worker.py',a,arm,str(s)) for s in range(3) for a in ['Full','binary'] for arm in ['H','L']]
 commands += [job('evaluation','evaluation','evaluate.py')]
 try:run_chain(commands)
 except subprocess.CalledProcessError as e:
  atomic_json(OUT/'PIPELINE_STOPPED.json',dict(attempt_id=ATTEMPT,status='stopped',command=e.cmd,returncode=e.returncode,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())));raise
 atomic_json(OUT/'PIPELINE_SUCCESS.json',dict(attempt_id=ATTEMPT,status='success',endpoints=12,updates_each=2000,evaluation_sha256=sha(OUT/'EVALUATION_COMPLETED.json'),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
if __name__=='__main__':main()
