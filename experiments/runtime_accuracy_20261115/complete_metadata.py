"""Attach frozen units and C++ predictions without altering measured outputs."""
from common_runtime import *
import math
def main():
    workload=read(O/'WORKLOADS.json')
    for kind in ['fem','native']:
        path=O/f'predictions_{kind}.jsonl';rs=list(map(json.loads,path.read_text().splitlines()));meta={g['table_id']:g for g in workload['groups'][kind]}
        for r in rs:r['unit']=meta[r['table_id']]['units']
        path.write_text(''.join(json.dumps(r)+'\n' for r in rs))
    qs=read(OLD/'native_replay_plan.json');reference={r['query_id']:r for r in rs if r['method']=='full' and r['batch_limit']==32};cpp=[]
    for line in (O/'native_cpp_raw.txt').read_text().splitlines():
        a=line.split(',')
        if a[0]!='prediction':continue
        q=qs[int(a[1])];r=dict(reference[q['query_id']]);r.update(method='native_cpp_validated',batch_limit=480,prediction=[float(v)*q['coordinate_scale']/1000 for v in a[2:]],timing_scope='resolved-table C++ long-loop amortization, not a service batch');cpp.append(r)
    assert len(cpp)==480
    (O/'native_cpp_predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in cpp))
    # The C++ compute grids must derive from exactly the same supplied knots,
    # not a denser native characterization unavailable to the other methods.
    tokens=iter((O/'native_kernel_input.txt').read_text().split());knots=[]
    for _ in range(int(next(tokens))):
        n=int(next(tokens));knots.append([[float(next(tokens)),float(next(tokens)),float(next(tokens))] for i in range(n)])
    assert int(next(tokens))==480
    supports=read(OLD/'native_supports.json');checks=[]
    for q in qs:
        ti,d=int(next(tokens)),int(next(tokens));assert d==q['raw_dbu'][1];k=knots[ti];t=supports[q['rule_key']];indices=sorted(range(len(t['coordinates'])),key=lambda i:t['coordinates'][i][1]);scale=q['coordinate_scale']
        coords=[t['coordinates'][i] for i in indices];vals=[t['labels'][i] for i in indices]
        same=len(k)==len(coords) and [r[0] for r in k]==[math.floor(x[1]*scale+.5) for x in coords]
        err=max(abs(r[j+1]*(scale/1000)-v[j]) for r,v in zip(k,vals) for j in range(2))/max(max(abs(z) for v in vals for z in v),1e-30) if len(k)==len(vals) else None
        check=dict(query_id=q['query_id'],table_id=q['rule_key'],support_count=len(coords),native_knots=len(k),same_coordinates=same,max_scaled_value_error=err,passed=same and err<1e-12);checks.append(check);assert check['passed']
    write(O/'native_support_equivalence.json',dict(passed=True,rows=checks))
if __name__=='__main__':main()
