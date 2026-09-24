"""Partition-scoped classical baselines; no model selection from test output."""
import argparse,json,time,collections
from pathlib import Path
import numpy as np
from .common import read_tables,write_json,file_hash
from .interpolation import predict
from .sampling import mask
from .metrics import record,summarize
from .train import unique_tables


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--partition',choices=['train','val','test'],default='val')
    p.add_argument('--methods',nargs='+',default=['linear','pchip','gp','idw','nearest'])
    p.add_argument('--seeds',nargs='+',type=int,default=[11,29,47,71,101])
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    tables=unique_tables([t for t in read_tables(a.data) if t['partition']==a.partition])
    summaries=[];records=[];skipped=[];start=time.perf_counter()
    for method in a.methods:
        for protocol in ('mcar','block','extrapolation','width'):
            ratios=[None] if protocol=='width' else [.1,.3,.5,.7]
            for ratio in ratios:
                for seed in a.seeds:
                    rs=[]
                    for t in tables:
                        if len(t['coordinates'])<2 or (protocol=='width' and t['width_count']<2):continue
                        x=np.array(t['coordinates']);y=np.array(t['labels'])
                        o,q=mask(x,protocol,ratio,seed)
                        try:pred,policy=predict(x[o],y[o],x[q],method)
                        except ValueError as exc:
                            skipped.append(dict(table_id=t['table_id'],method=method,protocol=protocol,reason=str(exc)));continue
                        rs.append(record(t,y[q],pred,method=method,protocol=protocol,ratio=ratio,seed=seed,interpolation=policy))
                    if rs:
                        summaries.append(dict(method=method,protocol=protocol,ratio=ratio,seed=seed,**summarize(rs)))
                        records.extend(rs)
    write_json(a.output/'results.json',dict(partition=a.partition,data_sha256=file_hash(a.data),
        elapsed_seconds=time.perf_counter()-start,records=records,summaries=summaries,skipped=skipped,
        purpose='baseline characterization; not learned-method superiority evidence'))
    lines=['# Classical baseline characterization','',f'Partition: {a.partition}; native rule units; no learned-model claims.','',
           '| Method | Protocol | Missing fraction | Seeds | Macro NRMSE mean |','|---|---|---:|---:|---:|']
    grouped=collections.defaultdict(list)
    for s in summaries:grouped[(s['method'],s['protocol'],s['ratio'])].append(s['nrmse'])
    for (method,protocol,ratio),values in grouped.items():
        lines.append(f'| {method} | {protocol} | {ratio} | {len(values)} | {np.mean(values):.6f} |')
    (a.output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(seconds=time.perf_counter()-start,records=len(records),tables=len(tables))))

if __name__=='__main__':main()
