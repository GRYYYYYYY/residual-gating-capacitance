"""Exact raw encode contract; no numerical tolerance or blanket equal_nan."""
import numpy as np

def assert_same_encoded(a,b):
 for key in ('features','anchor','gate','lower','upper'):
  x,y=np.asarray(a[key]),np.asarray(b[key])
  if x.shape!=y.shape or not np.isfinite(x).all() or not np.isfinite(y).all() or not np.array_equal(x,y):raise ValueError('encoding mismatch: '+key)
 va,vb=np.asarray(a['valid']),np.asarray(b['valid'])
 if va.dtype.kind!='b' or vb.dtype.kind!='b' or va.shape!=vb.shape or not np.array_equal(va,vb):raise ValueError('valid-mask mismatch')
 da,db=np.asarray(a['delta']),np.asarray(b['delta'])
 if da.ndim!=3 or db.ndim!=3 or da.shape!=db.shape or da.shape[:2]!=va.shape:raise ValueError('delta shape mismatch')
 for d in (da,db):
  if not np.isfinite(d[va]).all():raise ValueError('nonfinite applicable delta')
  if not np.isnan(d[~va]).all():raise ValueError('invalid raw-basis sentinel')
 if not np.array_equal(da[va],db[va]):raise ValueError('finite delta mismatch')
 for key in ('inside','observed','values','scales'):
  if not np.array_equal(a[key],b[key]):raise ValueError('encoding mismatch: '+key)
