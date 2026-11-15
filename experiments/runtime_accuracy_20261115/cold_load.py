"""Fresh-process startup; file-system page cache is NOT flushed."""
import time,sys
BOOT=(time.perf_counter(),time.process_time())
from common_runtime import *
def worker(kind,method):
    pin();import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    from common import full,controls
    from learning import load,DEST
    setting='to_asap7' if kind=='fem' else 'public';imports=elapsed(BOOT);t=stamp();members=0;scope=method
    if method=='full':models,sc=full(setting);members=len(models)
    elif method in ['binary','residual']:
        # Use existing validated loader; it loads Full scales plus both controls.
        models,sc=full(setting);models=controls(setting,sc);members=sum(len(v) for v in models.values())+3;scope='Full + Binary + Residual bundle (loader granularity)'
    elif method in ['mlp','cnp']:
        sel=read(DEST/f'{setting}_selection.json');models=[load(setting,method,sel[method]['lr'],seed) for seed in range(3)];members=3
    elif method=='attentioncap':
        import attention
        sel=read(attention.DEST/'to_asap7_selection.json');models=[]
        for seed in range(3):
            state=torch.load(attention.DEST/f'to_asap7_lr{sel["lr"]:g}_s{seed}/checkpoint.pt',map_location='cpu',weights_only=True);m=attention.build();m.load_state_dict(state['state_dict']);m.eval();models.append(m)
        members=3
    else:models=[]
    write(O/f'cold_worker_{kind}_{method}.json',dict(task=kind,method=method,imports=imports,load=elapsed(t),total=elapsed(BOOT),members_loaded=members,scope=scope,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
def main():
    pin();rows=[]
    for kind in ['fem','native']:
        for method in ['numerical','full','binary','mlp','cnp']+(['attentioncap'] if kind=='fem' else []):
            for block in range(3):
                start=time.perf_counter();p=subprocess.run([sys.executable,__file__,'worker',kind,method],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True);wall=time.perf_counter()-start
                r=read(O/f'cold_worker_{kind}_{method}.json');rows.append(dict(**r,block=block,whole_process_wall_s=wall))
    write(O/'cold_load.json',dict(rows=rows,scope='fresh interpreter and model load; OS page cache uncontrolled, not storage-cold latency; no target adaptation; bundled control loader explicitly identified'))
if __name__=='__main__':
    if len(sys.argv)>1:worker(sys.argv[2],sys.argv[3])
    else:main()
