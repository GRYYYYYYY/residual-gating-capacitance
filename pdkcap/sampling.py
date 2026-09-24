"""Label-blind masks, private query oracle, and deterministic adaptive selection."""
import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import rankdata


def geometry_order(x, candidates, initial=()):
    x=np.asarray(x,float); candidates=list(sorted(candidates)); chosen=list(initial)
    scale=np.ptp(x,axis=0); scale[scale==0]=1; z=(x-x.min(axis=0))/scale
    remaining=set(candidates)-set(chosen)
    while remaining:
        ids=sorted(remaining)
        if not chosen:
            score=np.linalg.norm(z[ids]-.5,axis=1)
        else: score=cdist(z[ids],z[chosen]).min(axis=1)
        i=ids[int(np.argmax(score))]; chosen.append(i); remaining.remove(i)
    return chosen


def mask(x, protocol, ratio, seed):
    x=np.asarray(x); n=len(x)
    if n<2: raise ValueError('need at least two points')
    rng=np.random.default_rng(seed)
    count=None if protocol=='width' else min(n-1,max(1,round(n*ratio)))
    axis=1 if x.shape[1]>1 and np.ptp(x[:,1]) else 0
    order=np.lexsort((np.arange(n),x[:,axis]))
    if protocol=='mcar': hidden=rng.choice(n,count,replace=False)
    elif protocol=='block':
        start=int(rng.integers(0,n-count+1)); hidden=order[start:start+count]
    elif protocol=='extrapolation': hidden=order[-count:]
    elif protocol=='width':
        widths=np.unique(x[:,0])
        if len(widths)<2: raise ValueError('whole-width holdout requires multiple widths')
        # All points at one held-out width; ratio does not manufacture a partial curve.
        hidden=np.flatnonzero(x[:,0]==widths[seed%len(widths)])
    else: raise ValueError(protocol)
    hidden=np.sort(hidden); observed=np.setdiff1d(np.arange(n),hidden)
    return observed,hidden


class QueryOracle:
    def __init__(self, labels, allowed, budget):
        self.__labels=np.array(labels,float,copy=True)
        self.allowed=frozenset(int(i) for i in allowed); self.budget=int(budget); self._seen={}
    def query(self,index):
        index=int(index)
        if index not in self.allowed: raise PermissionError('evaluation label is sealed')
        if index not in self._seen:
            if len(self._seen)>=self.budget: raise RuntimeError('query budget exhausted')
            self._seen[index]=self.__labels[index].copy()
        return self._seen[index].copy()
    @property
    def observations(self):
        ids=sorted(self._seen)
        return np.array(ids,int),np.array([self._seen[i] for i in ids],float)


def select(x, candidates, observed, predictions=None, interpolation=None, scales=None,
           strategy='farthest', seed=0):
    candidates=np.array(sorted(set(candidates)-set(observed)),int)
    if not len(candidates): raise ValueError('no candidates remain')
    if strategy=='random': return int(np.random.default_rng(seed).choice(candidates))
    if strategy=='farthest': return int(geometry_order(x,candidates,observed)[len(observed)])
    if strategy in ('learned','disagreement_only','residual_only'):
        p=np.asarray(predictions,float)
        if p.ndim!=3 or p.shape[0]<2 or p.shape[1]!=len(x): raise ValueError('aligned ensemble required')
        s=np.asarray(scales,float)
        if not np.isfinite(s).all() or (s<=0).any(): raise ValueError('positive frozen scales required')
        disagreement=(p.std(axis=0)/s).mean(axis=1)
        residual=(np.abs(p.mean(axis=0)-interpolation)/s).mean(axis=1)
        score=(rankdata(disagreement[candidates],method='average')+
               rankdata(residual[candidates],method='average'))/(2*len(candidates))
        if strategy=='disagreement_only':score=disagreement[candidates]
        if strategy=='residual_only':score=residual[candidates]
    elif strategy=='curvature':
        # Multi-axis geometry-aware local slope discrepancy; labels only via interpolator.
        z=np.asarray(x,float); scale=np.ptp(z,axis=0); scale[scale==0]=1; z=z/scale
        distances=cdist(z,z); values=np.asarray(interpolation,float)/np.asarray(scales,float)
        curvature=np.zeros(len(z))
        for i in candidates:
            neighbors=np.argsort(distances[i])[1:min(len(z),7)]
            delta=z[neighbors]-z[i]; rhs=values[neighbors]-values[i]
            gradient=np.linalg.lstsq(delta,rhs,rcond=None)[0]
            curvature[i]=np.mean(np.abs(rhs-delta@gradient))
        score=curvature[candidates]
    else: raise ValueError(strategy)
    return int(candidates[int(np.argmax(score))])
