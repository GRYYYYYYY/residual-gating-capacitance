"""Validate the C++ counterpart against every frozen native query, then time it."""
from common_runtime import *
import collections,ctypes,numpy as np
def main():
    pin();qs=read(OLD/'native_replay_plan.json');groups=collections.defaultdict(set)
    for q in qs:groups[(q['process'],q['design'])].add(q['provenance']['table_pointer'])
    knots={}
    for (proc,design),ptrs in groups.items():
        for line in (OLD/'native'/proc/design/'trace.tsv').open():
            a=line.rstrip().split('\t')
            if a[0]=='K' and a[1] in ptrs:knots.setdefault((proc,design,a[1]),[]).append([int(a[3]),float(a[4]),float(a[5])])
    keys=list(knots);assert all(len(knots[k])>=2 and knots[k][-1][0]!=100000 for k in keys)
    lines=[str(len(keys))]
    for key in keys:
        lines.append(str(len(knots[key])));lines.extend(' '.join(map(str,row)) for row in knots[key])
    lines.append(str(len(qs)))
    for q in qs:lines.append(f"{keys.index((q['process'],q['design'],q['provenance']['table_pointer']))} {q['raw_dbu'][1]}")
    inp=O/'native_kernel_input.txt';inp.write_text('\n'.join(lines)+'\n')
    flags=['-O3','-DNDEBUG','-std=c++17'];src=H/'native_lookup.cpp';exe=O/'native_lookup';lib=O/'native_lookup.so'
    for target,extra in [(exe,[]),(lib,['-shared','-fPIC'])]:subprocess.run(['g++',*flags,*extra,str(src),'-o',str(target)],check=True)
    t=stamp();out=subprocess.check_output([str(exe),str(inp)],text=True);process=elapsed(t);(O/'native_cpp_raw.txt').write_text(out)
    errors=[];rows=[];setup=None;pilot=None
    for line in out.splitlines():
        a=line.split(',')
        if a[0]=='prediction':
            i=int(a[1]);p=np.array(list(map(float,a[2:])));ref=np.array(qs[i]['native_prediction']);e=float(np.max(abs(p-ref))/max(abs(ref).max(),1e-30));errors.append(e);assert e<1e-12,(i,e)
        if a[0]=='timing':rows.append(dict(task='native',method='native_cpp_validated',block=int(a[1]),wall_s=float(a[2]),cpu_s=float(a[3]),inner_repetitions=int(a[4]),query_count=int(a[5]),checksum=float(a[6])))
        if a[0]=='setup':setup=a[1:]
        if a[0]=='pilot':pilot=a[1:]
    dll=ctypes.CDLL(str(lib));dll.load_tables.argtypes=[ctypes.c_char_p];assert dll.load_tables(str(inp).encode())==len(qs)
    dll.lookup.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_double)];buffer=(ctypes.c_double*2)();cross=[]
    for block in range(-3,20):
        t=stamp();check=0.
        for i in range(len(qs)):dll.lookup(i,buffer);check+=buffer[0]+buffer[1]
        r=dict(block=block,query_count=len(qs),checksum=check,**elapsed(t))
        if block>=0:cross.append(r)
    csvwrite(O/'native_kernel_timing.csv',rows);csvwrite(O/'native_ctypes_timing.csv',cross)
    write(O/'native_kernel_validation.json',dict(status='completed',queries=len(qs),passed=len(errors)==len(qs),max_scaled_error=max(errors),source_sha256=sha(src),input_sha256=sha(inp),compiler=subprocess.check_output(['g++','--version'],text=True),flags=flags,setup=setup,pilot=pilot,subprocess_wall=process,scope='source-validated C++ counterpart of finite, no-sentinel getComputeRC; resolved width/context. NOT linked OpenRCX or full getRC. Both returned components, no trace/debug IO in timed loop.',cross_boundary_scope='Python ctypes loop + argument marshaling + getter + checksum; no per-call latency distribution claimed',source_reference='OpenROAD 0b54bb3203e0895f87940ff982358a6e4d406e28 src/rcx/src/extRCmodel.cpp; preexisting validation covers 29735 trace records'))
if __name__=='__main__':main()
