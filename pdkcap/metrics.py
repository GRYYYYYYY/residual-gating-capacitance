import collections
import numpy as np


def record(table, truth, predicted, **metadata):
    truth=np.asarray(truth,float); predicted=np.asarray(predicted,float)
    if truth.shape!=predicted.shape or truth.size==0 or not np.isfinite(predicted).all():
        raise ValueError('invalid metric population')
    error=predicted-truth
    return dict(table_id=table['table_id'],split_group=table.get('split_group',table['table_id']),
                domain=table['domain'],process_id=table['process_id'],family=table['family'],
                unit=table['units'],n=len(truth),squared_error=(error**2).sum(axis=0).tolist(),
                squared_truth=(truth**2).sum(axis=0).tolist(),
                absolute_error=np.abs(error).sum(axis=0).tolist(),
                p95_absolute=np.quantile(np.abs(error),.95,axis=0).tolist(),**metadata)


def summarize(records):
    # Macro over process/family/target; never combine distinct domains or units.
    domains={(r['domain'],r['unit']) for r in records}
    if len(domains)!=1: raise ValueError('summary must contain one domain and unit')
    groups=collections.defaultdict(list)
    for r in records: groups[(r['process_id'],r['family'])].append(r)
    cells=[]; zero=[]
    for (process,family),rs in sorted(groups.items()):
        n=sum(r['n'] for r in rs)
        se=np.sum([r['squared_error'] for r in rs],axis=0)
        sy=np.sum([r['squared_truth'] for r in rs],axis=0)
        ae=np.sum([r['absolute_error'] for r in rs],axis=0)
        for j in range(len(se)):
            c=dict(process=process,family=family,target=j,n=n,rmse=float(np.sqrt(se[j]/n)),mae=float(ae[j]/n))
            if sy[j]>0: c['nrmse']=float(np.sqrt(se[j]/sy[j])); cells.append(c)
            else: zero.append(c)
    return dict(nrmse=float(np.mean([c['nrmse'] for c in cells])) if cells else None,
                cells=cells,zero_truth_groups=zero)
