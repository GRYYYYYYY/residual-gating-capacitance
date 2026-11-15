from common import *
from kernels import *
import itertools
rng=np.random.default_rng(20261115);rows=[]
for dtype in [np.float32,np.float64]:
 for d in [1,2,4]:
  axes=[np.array([0.,.17,1.],dtype=dtype)*(10.**(j*2-3)) for j in range(d)]
  x=np.array(list(itertools.product(*axes)),dtype=dtype);q=rng.random((30,d))*np.array([a[-1] for a in axes]);q=np.concatenate([q,x]);z=x/np.array([a[-1] for a in axes]);zq=q/np.array([a[-1] for a in axes])
  y=np.stack([np.ones(len(x)),z.sum(1),z.prod(1)],1);truth=np.stack([np.ones(len(q)),zq.sum(1),zq.prod(1)],1)
  pred,t=mli(x,y,q,False);err=float(np.max(abs(pred-truth)));assert err<3e-7
  perm=rng.permutation(len(x));assert np.allclose(mli(x[perm],y[perm],q)[0],pred)
  assert np.allclose(mli(x*1e6,y*1e12,q*1e6)[0]/1e12,pred)
  rows.append(dict(dtype=str(dtype),rank=d,queries=len(q),max_absolute=err,tests='constant,affine,mixed_product,nodes,endpoints,nonuniform,anisotropic,vector,order,unit_conversion'))
x=np.array([[0.,7],[1.,7]]);y=np.array([[2.,3],[4.,5]])
assert np.array_equal(mli(x,y,x)[0],y)
assert mli(x,y,[[-1,7],[2,7]])[1]==['explicit_clamp']*2
try:mli(np.array([[0],[0]]),np.array([[1],[2]]),[[0]]);raise AssertionError()
except ValueError:pass
x=np.array([[0,0],[1,0],[0,1]]);y=np.array([[1],[2],[3]])
try:mli(x,y,[[.5,.5]],False);raise AssertionError()
except ValueError:pass
assert mli(x,y,[[.5,.5]],True)[1]==['sparse_support_extension']
precision=[]
for dtype in [np.float32,np.float64]:
 for d in [1,2,4]:
  corners=np.array([[(m>>j)&1 for j in range(d)] for m in range(1<<d)],dtype=dtype)
  values=np.stack([corners.sum(1),corners.prod(1),np.ones(len(corners),dtype=dtype)],1);errors=[]
  for k in range(50):
   t=rng.random(d).astype(dtype);v=multilinear_cell(values,t,dtype);truth=np.array([t.sum(),t.prod(),1.],dtype=dtype);errors.append(float(np.max(abs(v-truth))));assert v.dtype==dtype
  assert max(errors)<(2e-6 if dtype==np.float32 else 1e-12)
  precision.append(dict(arithmetic=str(dtype),rank=d,maximum=max(errors),median=float(np.median(errors)),p95=float(np.quantile(errors,.95))))
write(O/'kernel_unit_tests.json',dict(passed=True,rows=rows,cell_arithmetic_precision=precision,experiment_arithmetic='float64',extra='constant/repeated axes, conflicting duplicate rejection, missing-corner rejection vs labeled extension, outside explicit clamp',commercial_equivalence_claim=False))
print('kernel unit tests passed')
