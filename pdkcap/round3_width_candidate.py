"""Unselected engineering candidate; frozen deployments still use round3_support."""
import numpy as np

def width_linear_grouped(x, values, query):
    x,y,q=np.asarray(x,float),np.asarray(values,float),np.asarray(query,float)
    if x.ndim!=2 or q.ndim!=2 or y.ndim!=2 or len(x)!=len(y) or x.shape[1]!=q.shape[1]:
        raise ValueError('unaligned support')
    if not all(np.isfinite(v).all() for v in (x,y,q)):raise ValueError('nonfinite support')
    unique,ids,inverse=np.unique(x,axis=0,return_index=True,return_inverse=True)
    if not np.array_equal(y,y[ids][inverse]):raise ValueError('conflicting duplicate observations')
    x,y=unique,y[ids]
    out=np.full((len(q),y.shape[1]),np.nan);valid=np.zeros(len(q),bool)
    groups={};queries={}
    for i,row in enumerate(x):groups.setdefault(tuple(row[1:]),[]).append(i)
    for i,row in enumerate(q):queries.setdefault(tuple(row[1:]),[]).append(i)
    for key,indices in queries.items():
        if key not in groups:continue
        support=np.asarray(groups[key]);qi=np.asarray(indices)
        widths=x[support,0];asked=q[qi,0];right=np.searchsorted(widths,asked)
        exact=(right<len(widths)) & (widths[np.minimum(right,len(widths)-1)]==asked)
        out[qi[exact]]=y[support[right[exact]]];valid[qi[exact]]=True
        between=~exact & (right>0) & (right<len(widths))
        lo=support[right[between]-1];hi=support[right[between]]
        weight=(asked[between]-x[lo,0])/(x[hi,0]-x[lo,0])
        out[qi[between]]=(1-weight[:,None])*y[lo]+weight[:,None]*y[hi]
        valid[qi[between]]=True
    return out,valid
