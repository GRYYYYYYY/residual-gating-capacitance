"""Frozen workloads and auditable timing utilities; no query truth in predictors."""
import os,sys,json,time,hashlib,csv,resource,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
H=Path(__file__).resolve().parent
O=R/'results/runtime_accuracy_20261115'; O.mkdir(parents=True,exist_ok=True)
OLD=R/'results/layout_offgrid_20261115'
UP=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026')
sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
def read(p): return json.loads(Path(p).read_text())
def write(p,x): Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvwrite(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open('w') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
def pin():
    cpu=int(os.environ.get('RUNTIME_CPU','24'));os.sched_setaffinity(0,{cpu})
    if 'torch' in sys.modules:
        torch=sys.modules['torch'];torch.set_num_threads(1)
        try:torch.set_num_interop_threads(1)
        except RuntimeError:pass
    return cpu
def stamp(): return time.perf_counter(),time.process_time()
def elapsed(t): return {'wall_s':time.perf_counter()-t[0],'cpu_s':time.process_time()-t[1]}
def workloads(kind):
    if kind=='native':
        ts=read(OLD/'native_supports.json'); qs=read(OLD/'native_replay_plan.json')
        for q in qs:q['table_id']=q['rule_key']
    else:
        ts={t['table_id']:t for t in map(json.loads,(R/'runs/reference_dataset_v2/tables.jsonl').read_text().splitlines())}
        refs={r['query_id']:r for r in map(json.loads,(OLD/'predictions_fem.jsonl').read_text().splitlines()) if r['method']=='full'}
        qs=[dict(q,reference=refs[q['query_id']]['reference']) for q in read(OLD/'reference_plan.json')['queries'] if q['split']=='formal']
    groups=[]
    for tid in sorted(set(q['table_id'] for q in qs)):
        groups.append((ts[tid],sorted([q for q in qs if q['table_id']==tid],key=lambda q:q['geometry_hash'])))
    return groups
def environment():
    import numpy,scipy,torch,platform
    cpu=pin();torch.set_num_threads(1)
    try:torch.set_num_interop_threads(1)
    except RuntimeError:pass
    data=dict(cpu=cpu,affinity=sorted(os.sched_getaffinity(0)),lscpu=subprocess.check_output(['lscpu'],text=True),python=sys.version,executable=sys.executable,numpy=numpy.__version__,scipy=scipy.__version__,torch=torch.__version__,torch_threads=torch.get_num_threads(),interop_threads=torch.get_num_interop_threads(),platform=platform.platform(),gpu_available=torch.cuda.is_available(),thread_environment={k:os.environ.get(k) for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']},git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),timing_clock=time.get_clock_info('perf_counter')._asdict() if hasattr(time.get_clock_info('perf_counter'),'_asdict') else str(time.get_clock_info('perf_counter')),policy='one benchmark worker, pinned CPU; shared host, no exclusive reservation or fixed frequency; no concurrent task benchmarks',cache='OS page cache uncontrolled; explicitly warmed inference; no answer cache; no Transformer support-state cache')
    for k in ['scaling_governor','scaling_cur_freq','cpuinfo_max_freq']:
        p=Path(f'/sys/devices/system/cpu/cpu{cpu}/cpufreq/{k}');data[k]=p.read_text().strip() if p.exists() else None
    try:
        from threadpoolctl import threadpool_info
        data['threadpools']=threadpool_info()
    except ImportError:pass
    write(O/'environment.json',data)
