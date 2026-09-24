"""Whole-pattern paired bootstrap of the exact mean-over-seeds NRMSE estimand."""
import collections
import numpy as np


def mean_seed_bootstrap(left,right,repeats=2000,seed=20260917):
    def arrange(records):
        result=collections.defaultdict(dict)
        for r in records:
            key=(r['training_seed'],r['sampling_seed'])
            result[key][r['table_id']]=r
        return result
    a=arrange(left);b=arrange(right);keys=sorted(a,key=lambda k:(-1 if k[0] is None else k[0],k[1]))
    population=sorted(next(iter(a.values())))
    n=len(population);sample=next(iter(a.values()));strata=collections.defaultdict(lambda:collections.defaultdict(list))
    for i,name in enumerate(population):
        r=sample[name];strata[(r['process_id'],r['family'])][r['split_group']].append(i)
    membership=np.zeros((n,len(strata)))
    for j,clusters in enumerate(strata.values()):
        for indices in clusters.values():membership[indices,j]=1
    la=[];rb=[];sy=[]
    for key in keys:
        right_key=key if key in b else (None,key[1])
        if right_key not in b or sorted(a[key])!=population or sorted(b[right_key])!=population:raise ValueError('unpaired seed/table population')
        for name in population:
            x=a[key][name];y=b[right_key][name]
            for field in ('n','squared_truth','process_id','family','split_group','domain','unit'):
                if x[field]!=y[field]:raise ValueError(f'unpaired {field}')
        la.append([a[key][name]['squared_error'] for name in population]);rb.append([b[right_key][name]['squared_error'] for name in population]);sy.append([a[key][name]['squared_truth'] for name in population])
    la=np.array(la);rb=np.array(rb);sy=np.array(sy)
    def score(errors,weights):
        e=np.einsum('ktd,bt,tg->bkgd',errors,weights,membership,optimize=True)
        truth=np.einsum('ktd,bt,tg->bkgd',sy,weights,membership,optimize=True)
        eligible=truth>0
        ratio=np.sqrt(np.divide(e,truth,out=np.zeros_like(e),where=eligible))
        counts=eligible.sum(axis=(2,3))
        if (counts==0).any():raise ValueError('no eligible pooled truth')
        return (ratio.sum(axis=(2,3))/counts).mean(axis=1)
    weights=np.ones((1,n));point=float(score(la,weights)[0]-score(rb,weights)[0])
    if all(len(g)<2 for g in strata.values()):return dict(mean_seed_difference=point,confidence_95=None,resamples=0,seed_cells=len(keys),reason='one pattern group per stratum')
    rng=np.random.default_rng(seed);differences=[]
    for start in range(0,repeats,50):
        batch=min(50,repeats-start);weights=np.zeros((batch,n))
        for j in range(batch):
            for clusters in strata.values():
                ids=sorted(clusters)
                for idx in rng.integers(0,len(ids),len(ids)):weights[j,clusters[ids[idx]]]+=1
        differences.extend((score(la,weights)-score(rb,weights)).tolist())
    return dict(mean_seed_difference=point,confidence_95=np.quantile(differences,[.025,.975]).tolist(),resamples=repeats,
        seed_cells=len(keys),pattern_groups=sum(len(s) for s in strata.values()),
        interpretation='paired pattern resampling shared across all frozen seeds; seed draws are not resampled or counted as independent designs')
