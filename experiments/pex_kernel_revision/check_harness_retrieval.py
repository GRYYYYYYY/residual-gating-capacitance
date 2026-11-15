from common import *
import gzip,subprocess
import numpy as np
rs=[json.loads(l) for l in gzip.open(O/'physical_predictions.jsonl.gz','rt')];checks=[]
for p in sorted(O.glob('harness_*_*.txt')):
 stem=p.stem[len('harness_'):];tid,mode=stem.rsplit('_',1);method='openrcx_kernel' if mode=='pass' else mode+'_compute';rr=[r for r in rs if r['table_id']==tid and r['method']==method]
 proc=subprocess.run([str(O/'pinned_kernel')],input=p.read_text(),text=True,capture_output=True,check=True);v=np.array([[float(a) for a in line.split()] for line in proc.stdout.splitlines()]);expected=np.array([r['prediction'] for r in rr]);scale=np.maximum(np.max(abs(expected),axis=0),1e-30);err=float(np.max(abs(v[:,2:]-expected)/scale));assert err<1e-12,(p,err)
 checks.append(dict(input=str(p.relative_to(R)),sha256=sha(p),method=method,queries=len(rr),max_scaled_error=err))
assert len(checks)==18
write(O/'pinned_storage_retrieval_checks.json',dict(passed=True,checks=checks,kernel_sha256=sha(H/'pinned_kernel.cpp'),array_header_sha256=sha(H/'pinned_array1.h'),scope='Exact pinned Array1D and function bodies; minimal allocation wrapper; finite no-sentinel inputs only'))
print('18 stored FEM harness cases verified with pinned Array1D')
