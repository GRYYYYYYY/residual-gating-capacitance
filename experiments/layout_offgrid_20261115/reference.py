"""Run frozen three-level direct field solves; keep every failure and matrix."""
import os,json,sys,copy,time,subprocess,hashlib,concurrent.futures
from pathlib import Path
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;O=R/'results/layout_offgrid_20261115'
OLD=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/pdkcap-v0/runs/reference_full_v2')
PY=OLD.parents[1]/'local/venv/bin/python'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(task):
 q,level=task;dest=O/'reference_results'/q['query_id']/level;dest.mkdir(parents=True,exist_ok=True)
 spec=copy.deepcopy(q['spec']);spec['h']*=1 if level=='coarse' else .5
 if level=='wide':spec['extent']*=2;spec['materials'][-1][0]=spec['extent']
 sp=dest/'spec.json';sh=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
 if (dest/'receipt.json').exists():
  rec=json.loads((dest/'receipt.json').read_text());assert rec['spec_hash']==sh and rec['solver_sha256']==sha(OLD/'fem_source_snapshot.py');assert rec.get('result_sha256')==sha(dest/'result.json');return rec
 sp.write_text(json.dumps(spec,indent=2));env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LD_LIBRARY_PATH='/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/workspaces/process-adapt-v3/local/sysroot/usr/lib/x86_64-linux-gnu')
 start=time.perf_counter()
 cmd=['/usr/bin/time','-f','%U %S','-o',str(dest/'cpu.txt'),str(PY),str(H/'reference_worker.py'),str(OLD/'fem_source_snapshot.py'),str(sp),str(dest)]
 try:
  with (dest/'worker.log').open('w') as f:r=subprocess.Popen(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);r.wait(timeout=180)
  status='completed' if r.returncode==0 else 'failed'
 except subprocess.TimeoutExpired:
  import signal
  os.killpg(r.pid,signal.SIGKILL);r.wait();status='timeout'
 # timeout charged conservatively at full wall time for one single-thread worker.
 cpu=(sum(map(float,(dest/'cpu.txt').read_text().split()[-2:])) if (dest/'cpu.txt').exists() and (dest/'cpu.txt').read_text().strip() else time.perf_counter()-start)
 rec=dict(query_id=q['query_id'],level=level,status=status,spec_hash=sh,solver_sha256=sha(OLD/'fem_source_snapshot.py'),cpu_s=cpu,wall_s=time.perf_counter()-start)
 if (dest/'result.json').exists():rec['result_sha256']=sha(dest/'result.json')
 (dest/'receipt.json').write_text(json.dumps(rec,indent=2));print(q['query_id'],level,status,round(rec['wall_s'],2),flush=True);return rec
if __name__=='__main__':
 phase=sys.argv[1] if len(sys.argv)>1 else 'pilot';plan=json.loads((O/('reference_plan_controls.json' if phase=='control' else 'reference_plan.json')).read_text())
 qs=[q for q in plan['queries'] if q['split']==phase]
 tasks=[(q,lev) for q in qs for lev in ['coarse','fine','wide']]
 # Fixed max 96 geometries *3*180s plus limited controls is below 64 core-hours.
 assert len(tasks)*180<56*3600
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,tasks))
 (O/f'reference_{phase}_ledger.json').write_text(json.dumps(results,indent=2))
