import json,sys,time,importlib.util,resource
from pathlib import Path
source,sp,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
m=importlib.util.spec_from_file_location('frozen_fem',source);fem=importlib.util.module_from_spec(m);m.loader.exec_module(fem)
spec=json.loads(sp.read_text());t=time.perf_counter();c=time.process_time()
r=fem.run_case(spec,out);r.update(cpu_s=time.process_time()-c,wall_s=time.perf_counter()-t,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
(out/'result.json').write_text(json.dumps(r))
