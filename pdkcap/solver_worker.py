"""One solver case per process; parent enforces timeout and retains failures."""
import argparse,importlib.util,json,resource,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,12*1024**3))
spec=importlib.util.spec_from_file_location('pdkcap_reused_fem',a.source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=time.perf_counter();cpu=time.process_time()
result=module.run_case(json.loads(a.spec.read_text()),a.output)
result.update(wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
(a.output/'result.json').write_text(json.dumps(result,indent=2))
