"""Remove unused union construction from retained-fit pointwise query paths.
Recheck identical predictions; never cache a geometry's answer.
"""
from common_runtime import *
from benchmark import Engine
import numpy as np,torch
def main():
    pin();torch.set_num_threads(1);audit=[];start=stamp()
    for kind in ['fem','native']:
        e=Engine(kind);groups=workloads(kind);methods=['mlp_adapt']+(['attentioncap_adapted'] if kind=='fem' else [])
        legacy={(r['table_id'],r['query_id']):r['prediction'] for r in map(json.loads,(OLD/f'predictions_{kind}.jsonl').read_text().splitlines()) if r['method']=='mlp_adapt'};legacy_checks=[]
        for t,qs in groups:
            e.prepare(t,qs)
            # Fresh execution of the unmodified, full S+Q original prediction
            # path, including its support-only fit; not used for warm timing.
            assert len(qs)<=32
            g,o,v,ix=e.union(t,qs);original=e.p('mlp_adapt',g,o,v)[ix]
            ref=np.array([legacy[t['table_id'],q['query_id']] for q in qs]);ys=np.asarray(e.p.scales['targets'][t['family']]);err=float(np.max(abs(original-ref)/ys));assert err<2e-6
            legacy_checks.append(dict(table_id=t['table_id'],source_scaled_error=err,passed=True))
        refs={(r['method'],r['batch_limit'],r['query_id']):r['prediction'] for r in map(json.loads,(O/f'predictions_{kind}.jsonl').read_text().splitlines()) if r['method'] in methods}
        raw=[];rng=np.random.default_rng(20261115)
        for size in [32,1,8]:
            jobs=[(m,t,qs[j:j+size],j) for m in methods for t,qs in groups for j in range(0,len(qs),size)]
            for block in range(-3,20):
                for k in rng.permutation(len(jobs)):
                    m,t,qs,j=jobs[k];p,st=e.predict(m,t,qs)
                    if block==0:
                        for q,pp in zip(qs,p):assert np.array_equal(pp,np.array(refs[m,size,q['query_id']])),(kind,m,size,q['query_id'])
                    if block>=0:raw.append(dict(task=kind,method=m,batch_limit=size,block=block,table_id=t['table_id'],batch_start=j,query_count=len(qs),support_count=len(t['coordinates']),cache_mode='weights and support-fit resident; Q-only geometry encoding; no answer cache',**st))
        path=O/f'timing_{kind}.csv';prior=list(csv.DictReader(path.open()));csvwrite(O/f'cached_union_initial_{kind}.csv',[r for r in prior if r['method'] in methods]);csvwrite(path,[r for r in prior if r['method'] not in methods]+raw)
        audit.append(dict(task=kind,methods=methods,passed=True,exact_predictions=True,timed_rows=len(raw),repeated_fit_for_validation=e.prep,original_canonical_S_plus_Q=legacy_checks,reason='Remove unused S+Q construction for pointwise retained-fit models; no algorithm or parameter change'))
    write(O/'cached_query_equivalence.json',dict(rows=audit,**elapsed(start)))
if __name__=='__main__':main()
