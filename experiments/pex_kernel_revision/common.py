import os,sys,json,csv,hashlib,time,resource
from pathlib import Path
R=Path(__file__).resolve().parents[2]; H=Path(__file__).resolve().parent; O=R/'results/pex_kernel_revision';O.mkdir(exist_ok=True)
UP=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026')
SRC=UP/'tools/OpenROAD-flow-scripts/tools/OpenROAD'; BUILD=SRC/'build-cpu-20260909'
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def csvwrite(p,rs):
 if not rs:return
 with Path(p).open('w') as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)),lineterminator='\n');w.writeheader();w.writerows(rs)
def pin():
 os.sched_setaffinity(0,{int(os.environ.get('RUNTIME_CPU','24'))})
 if 'torch' in sys.modules:sys.modules['torch'].set_num_threads(1)
def stamp():return time.perf_counter(),time.process_time()
def elapsed(t):return dict(wall_s=time.perf_counter()-t[0],cpu_s=time.process_time()-t[1])
