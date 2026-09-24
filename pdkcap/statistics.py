"""Paired whole-pattern cluster bootstrap; seed variation is reported separately."""
import collections
import numpy as np
from .metrics import summarize


def bootstrap_difference(left,right,repeats=2000,seed=20260917):
    l={r['table_id']:r for r in left};r={r['table_id']:r for r in right}
    if set(l)!=set(r):raise ValueError('paired reports must contain identical tables')
    strata=collections.defaultdict(lambda:collections.defaultdict(list))
    for key,a in l.items():
        b=r[key]
        for field in ('domain','unit','process_id','family','n','squared_truth','split_group'):
            if a[field]!=b[field]:raise ValueError(f'paired population differs: {field}')
        strata[(a['process_id'],a['family'])][a['split_group']].append(key)
    if all(len(clusters)<2 for clusters in strata.values()):
        return dict(left_minus_right=summarize(left)['nrmse']-summarize(right)['nrmse'],
            confidence_95=None,resamples=0,seed=seed,
            interpretation='Population interval unavailable: only one independent pattern group per stratum. Report seed variation, not a degenerate bootstrap interval.')
    rng=np.random.default_rng(seed);samples=[]
    for _ in range(repeats):
        ids=[]
        for clusters in strata.values():
            keys=sorted(clusters)
            for i in rng.integers(0,len(keys),len(keys)):ids.extend(clusters[keys[i]])
        a=summarize([l[i] for i in ids])['nrmse'];b=summarize([r[i] for i in ids])['nrmse']
        if a is None or b is None:raise ValueError('no nonzero pooled truth group')
        samples.append(a-b)
    return dict(left_minus_right=summarize(left)['nrmse']-summarize(right)['nrmse'],
        confidence_95=np.quantile(samples,[.025,.975]).tolist(),resamples=repeats,seed=seed,
        interpretation='conditional on fixed training/sampling seed; whole duplicate-linked patterns resampled')
