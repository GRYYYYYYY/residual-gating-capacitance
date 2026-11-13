"""One-owner bounded local queue, exclusive receipts and per-job timeout."""
import os,sys,json,time,subprocess,concurrent.futures
from pathlib import Path
from common import ROOT,HERE,write,sha
R=ROOT/'results/dac_characterization_20261114'
mode=sys.argv[1]
if mode=='validation':
    cmds=[[sys.executable,str(HERE/'evaluate.py'),'--setting',s,'--split','val','--numerical-selection','--workers','1','--out',str(R/f'validation_{s}')] for s in ('public','reference','to_asap7')]
elif mode=='learning':cmds=[[sys.executable,str(HERE/'learning.py'),'--setting',s] for s in ('public','reference','to_asap7')]
elif mode=='confirmation':cmds=[[sys.executable,str(HERE/'evaluate.py'),'--setting',s,'--workers','1','--out',str(R/f'confirmation_{s}')] for s in ('public','reference','to_asap7')]
else:raise ValueError(mode)
folder=R/f'queue_{mode}';folder.mkdir(exist_ok=False)
write(folder/'FROZEN.json',dict(commands=cmds,max_concurrency=3,timeout_seconds=7200,code_sha256=sha(__file__),pid=os.getpid(),started=time.time()))
def run(item):
 i,cmd=item;start=time.perf_counter()
 with (folder/f'{i}.log').open('x') as f:
  try:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=7200,cwd=ROOT);status=dict(exit_code=r.returncode)
  except subprocess.TimeoutExpired:status=dict(exit_code=None,reason='7200 second timeout')
 write(folder/f'{i}.json',dict(command=cmd,elapsed_seconds=time.perf_counter()-start,**status));return status
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rs=list(pool.map(run,enumerate(cmds)))
write(folder/'COMPLETED.json',dict(results=rs));print(mode,rs,flush=True)
