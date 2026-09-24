"""Observed-only interpolation. Every extrapolation rule is explicit."""
import numpy as np
from scipy.interpolate import LinearNDInterpolator, PchipInterpolator, RegularGridInterpolator
from scipy.spatial import QhullError
from scipy.spatial.distance import cdist


def reduce_coordinates(x, query):
    x=np.asarray(x, dtype=float); query=np.asarray(query, dtype=float)
    if x.ndim!=2 or query.ndim!=2 or x.shape[1]!=query.shape[1]:
        raise ValueError('coordinate dimensions differ')
    origin=x.min(axis=0); scale=np.ptp(x,axis=0); scale[scale==0]=1
    a=(x-origin)/scale; b=(query-origin)/scale
    # Keep independent axes of the support affine span, not duplicated left/right spacing.
    axes=[]; rank=0
    for j in range(a.shape[1]):
        candidate=axes+[j]
        nr=np.linalg.matrix_rank(a[:,candidate]-a[0,candidate],tol=1e-10)
        if nr>rank: axes=candidate; rank=nr
    return a[:,axes],b[:,axes],axes


def predict(x, y, query, method='linear'):
    x=np.asarray(x, dtype=float); y=np.asarray(y, dtype=float); query=np.asarray(query,dtype=float)
    if len(x)==0 or len(x)!=len(y) or y.ndim!=2:
        raise ValueError('nonempty aligned support and 2D targets required')
    if not all(np.isfinite(v).all() for v in (x,y,query)):
        raise ValueError('non-finite input')
    # Repeated observations must agree; never silently average conflicting labels.
    ux,indices,inverse=np.unique(x,axis=0,return_index=True,return_inverse=True)
    if not np.array_equal(y, y[indices][inverse]): raise ValueError('conflicting duplicate coordinates')
    x=ux; y=y[indices]
    a,b,axes=reduce_coordinates(x,query)
    if not axes:
        pred=np.repeat(y[:1],len(query),axis=0); policy='constant-degenerate'
    else:
        d=cdist(b,a); nearest=y[d.argmin(axis=1)]
        policy='nearest-outside-support'
        if method=='nearest': pred=nearest
        elif method=='idw':
            w=1/np.maximum(d,1e-12)**2
            pred=w@y/w.sum(axis=1,keepdims=True); policy='all-observed-inverse-square'
        elif method=='gp':
            # Fixed prior/kernel, no hidden labels or test-time hyperparameter tuning.
            dd=cdist(a,a); positive=dd[dd>0]
            ell=np.median(positive) if len(positive) else 1.
            k=np.exp(-.5*(dd/ell)**2)+1e-6*np.eye(len(a))
            mean=y.mean(axis=0)
            pred=mean+np.exp(-.5*(d/ell)**2)@np.linalg.solve(k,y-mean)
            policy='RBF-GP-fixed-median-support-lengthscale'
        elif method in ('linear','pchip','bilinear'):
            if len(axes)==1:
                order=np.argsort(a[:,0]); xx=a[order,0]; yy=y[order]
                clipped=np.clip(b[:,0],xx[0],xx[-1])
                if method=='pchip' and len(a)>1:
                    pred=PchipInterpolator(xx,yy,axis=0)(clipped)
                else:
                    pred=np.column_stack([np.interp(clipped,xx,yy[:,j]) for j in range(y.shape[1])])
                policy='one-dimensional-boundary-clamp'
            elif method=='pchip':
                raise ValueError('PCHIP is defined only for one-dimensional support')
            else:
                grid=[np.unique(a[:,j]) for j in range(a.shape[1])]
                full=int(np.prod([len(g) for g in grid]))==len(a)
                if method=='bilinear' and full and len(axes)==2:
                    values=np.empty(tuple(len(g) for g in grid)+(y.shape[1],))
                    for xi,yi in zip(a,y): values[tuple(np.searchsorted(g,v) for g,v in zip(grid,xi))]=yi
                    clipped=np.column_stack([np.clip(b[:,j],g[0],g[-1]) for j,g in enumerate(grid)])
                    pred=RegularGridInterpolator(grid,values)(clipped); policy='bilinear-boundary-clamp'
                else:
                    try:
                        pred=np.asarray(LinearNDInterpolator(a,y)(b)).reshape(len(b),y.shape[1])
                        outside=~np.isfinite(pred).all(axis=1); pred[outside]=nearest[outside]
                        policy='simplex-linear-nearest-outside-hull'
                    except QhullError:
                        pred=nearest; policy='nearest-degenerate-hull'
                    if method=='bilinear': policy='incomplete-grid-fallback:'+policy
        else: raise ValueError(f'unknown method: {method}')
    pred=np.maximum(pred,0.)
    # Exact support fidelity (also for GP smoothing).
    for i,q in enumerate(query):
        same=np.flatnonzero(np.all(x==q,axis=1))
        if len(same): pred[i]=y[same[0]]
    return pred,dict(method=method,policy=policy,support_axes=axes,support_count=len(x))
