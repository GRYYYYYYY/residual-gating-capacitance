"""Paired whole-associated-group intervals for public rules only."""
from collections import defaultdict
import numpy as np


def paired_interval(left,right,repeats=2000,seed=20260918):
    def index(rows):
        output={}
        for row in rows:
            key=(row['table_id'],row['mask_seed'])
            if key in output:raise ValueError('duplicate table/mask in comparison')
            output[key]=row
        return output
    a,b=index(left),index(right)
    if not a or a.keys()!=b.keys():
        return dict(ci95=None,reason='unpaired or empty population')
    strata=defaultdict(list);membership=defaultdict(set)
    for key,row in a.items():
        other=b[key]
        if row['n']!=other['n'] or row['population_sha256']!=other['population_sha256']:
            return dict(ci95=None,reason='expert applicability differs; no matched full-query comparison')
        if row['domain']!='public_rules' or other['domain']!='public_rules':
            return dict(ci95=None,reason='related layers in existing stacks; independent population not established')
        np.testing.assert_array_equal(row['squared_truth'],other['squared_truth'])
        group=(row['process_id'],row['family'])
        strata[group].append(key);membership[row['split_group']].add(group)
    if any(len(v)>1 for v in membership.values()):
        return dict(ci95=None,reason='associated group spans strata; independent stratum resampling invalid')
    rng=np.random.default_rng(seed);parts=[[],[]];counts={}
    for stratum,keys in sorted(strata.items()):
        groups=sorted({a[key]['split_group'] for key in keys});masks=sorted({a[key]['mask_seed'] for key in keys})
        counts['/'.join(stratum)]=len(groups)
        if len(groups)<2:return dict(ci95=None,reason='singleton associated-group stratum',group_counts=counts)
        gi={v:i for i,v in enumerate(groups)};mi={v:i for i,v in enumerate(masks)}
        shape=(len(groups),len(masks),len(a[keys[0]]['squared_truth']))
        aa=np.zeros(shape);bb=np.zeros(shape);yy=np.zeros(shape)
        for key in keys:
            i,j=gi[a[key]['split_group']],mi[a[key]['mask_seed']]
            aa[i,j]+=a[key]['squared_error'];bb[i,j]+=b[key]['squared_error'];yy[i,j]+=a[key]['squared_truth']
        weights=np.vstack([np.ones(len(groups)),rng.multinomial(len(groups),np.full(len(groups),1/len(groups)),size=repeats)])
        den=np.einsum('bg,gst->bst',weights,yy)
        for values,destination in zip((aa,bb),parts):
            num=np.einsum('bg,gst->bst',weights,values);ratio=np.full_like(num,np.nan)
            np.divide(num,den,out=ratio,where=den>0);destination.append(np.sqrt(ratio))
    def mean(values):
        values=np.concatenate(values,axis=2)
        finite=np.isfinite(values);count=finite.sum(axis=2)
        total=np.where(finite,values,0).sum(axis=2)
        per_mask=np.full_like(total,np.nan);np.divide(total,count,out=per_mask,where=count>0)
        good=np.isfinite(per_mask)
        return np.divide(np.where(good,per_mask,0).sum(axis=1),good.sum(axis=1),
            out=np.full(len(per_mask),np.nan),where=good.sum(axis=1)>0)
    delta=mean(parts[0])-mean(parts[1])
    if not np.isfinite(delta).all():return dict(ci95=None,reason='undefined all-zero-truth bootstrap estimand')
    return dict(delta=float(delta[0]),ci95=np.quantile(delta[1:],[.025,.975]).tolist(),replicates=repeats,
        group_counts=counts,estimand='mean across masks of process/family/component macro NRMSE difference',
        scope='paired associated groups; seeds are not independent population samples; descriptive, no multiple-comparison correction')
