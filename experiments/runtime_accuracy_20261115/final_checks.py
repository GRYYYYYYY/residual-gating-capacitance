"""Scientific population, timing-accounting and deployment consistency checks."""
from common_runtime import *
import math,collections
def main():
    rows=list(csv.DictReader((O/'timing_raw.csv').open()));groups=collections.defaultdict(list)
    for r in rows:groups[r['task'],r['method'],int(r['batch_limit']),int(r['block'])].append(r)
    for (task,method,b,block),rr in groups.items():
        assert sum(int(r['query_count']) for r in rr)==(71 if task=='fem' else 480)
        assert len({r['batch_id'] for r in rr})==len(rr)
        for r in rr:
            assert float(r['wall_s'])>0 and float(r['cpu_s'])>=0
            stage=sum(float(r[k]) for k in ['setup_s','adapt_s','encode_s','numerical_s','forward_s','transfer_s','postprocess_s'])
            assert 0<=stage<=float(r['wall_s'])+1e-6,(task,method,stage,r['wall_s'])
    for task,method,b in {k[:3] for k in groups}:assert {k[3] for k in groups if k[:3]==(task,method,b)}==set(range(20))
    for task in ['fem','native']:
        rr=list(map(json.loads,(O/f'predictions_{task}.jsonl').read_text().splitlines()));sets=[]
        for m,b in set((r['method'],r['batch_limit']) for r in rr):
            sub=[r for r in rr if r['method']==m and r['batch_limit']==b];sets.append({r['query_id'] for r in sub})
            assert all(all(math.isfinite(x) for x in r['prediction']) for r in sub)
        assert all(s==sets[0] for s in sets)
    eq=read(O/'OUTPUT_EQUIVALENCE.json');assert eq['passed']
    assert eq['checks']['native_support_equivalence']['passed']
    for k in ['cnp_staged_equivalence','cached_query_equivalence']:
        if k in eq['checks']:
            val=eq['checks'][k];rr=val['rows'] if isinstance(val,dict) else val;assert all(r['passed'] for r in rr)
    solver=read(O/'solver_task_match.json');sr=list(map(json.loads,(O/'solver_raw.jsonl').read_text().splitlines()))
    assert len(sr)==213 and {r['query_id'] for r in sr}==set(solver['query_ids'])
    assert all(r['rhs_count']==1 and r['column_scaled_error']<1e-8 for r in sr)
    flow=read(O/'native_flow_completed.json');assert flow['runs']==96 and flow['trace_enabled'] is False
    for p in (O/'native').glob('*/*/*/*/receipt.json'):assert read(p)['identical_frozen_variant']
    assert len(list((O/'native').glob('*/*/*/*/receipt.json')))==96
    pre=read(O/'rule_preparation.json');assert len(pre['rows'])==12 and all(r['equal_frozen_export'] for r in pre['rows'])
    assert read(O/'SUMMARY.json')['accounted_main_cpu_core_hours']<8
    write(O/'CHECKS.json',dict(passed=True,timing_rows=len(rows),timing_groups=len(groups),canonical_equivalence=True,same_query_pairing=True,solver_rows=len(sr),native_runs=96,fixed_node_exports=12,source_training=False,scope='query replay, matched 2D template solve, same-node offline native extraction; no node enrichment or online model substitution'))
    print('all runtime/accuracy scientific checks passed')
if __name__=='__main__':main()
