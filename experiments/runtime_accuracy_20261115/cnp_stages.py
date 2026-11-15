"""Replace combined CNP timings with a repeated, exactly equivalent staged run.
Retain the superseded measurements locally for the measurement audit.
"""
from common_runtime import *
from benchmark import Engine
import numpy as np,torch
def main():
    pin();torch.set_num_threads(1);audit=[]
    for kind in ['fem','native']:
        e=Engine(kind);groups=workloads(kind);raw=[];rng=np.random.default_rng(20261115)
        refs={(r['batch_limit'],r['query_id']):r['prediction'] for r in map(json.loads,(O/f'predictions_{kind}.jsonl').read_text().splitlines()) if r['method']=='cnp'}
        for size in [32,1,8]:
            jobs=[(t,qs[j:j+size],j) for t,qs in groups for j in range(0,len(qs),size)]
            for block in range(-3,20):
                for k in rng.permutation(len(jobs)):
                    t,qs,j=jobs[k];p,st=e.predict('cnp',t,qs)
                    if block==0:
                        for q,pp in zip(qs,p):assert np.array_equal(pp,np.array(refs[size,q['query_id']])),(kind,size,q['query_id'])
                    if block>=0:raw.append(dict(task=kind,method='cnp',batch_limit=size,block=block,table_id=t['table_id'],batch_start=j,query_count=len(qs),support_count=len(t['coordinates']),cache_mode='weights resident; original three encodings and all S+Q forwards; no answer cache',**st))
        path=O/f'timing_{kind}.csv';prior=list(csv.DictReader(path.open()));old=[r for r in prior if r['method']=='cnp'];csvwrite(O/f'cnp_combined_initial_{kind}.csv',old);csvwrite(path,[r for r in prior if r['method']!='cnp']+raw)
        audit.append(dict(task=kind,passed=True,exact_predictions=True,timed_rows=len(raw),cpu_s=sum(r['cpu_s'] for r in raw),reason='Expose original encoding, three forwards and assembly separately; not a faster-algorithm search'))
    write(O/'cnp_staged_equivalence.json',audit)
if __name__=='__main__':main()
