"""Specified tensor MLI and pinned OpenRCX finite-grid reproduction.
No commercial source; sparse support/clamping are explicitly our extensions.
"""
import itertools
import numpy as np

def independent_axes(x):
 axes=[]
 for j in range(x.shape[1]):
  if np.ptp(x[:,j])<=1e-14:continue
  if any(np.allclose(x[:,j],x[:,k],rtol=0,atol=1e-14) for k in axes):continue
  axes.append(j)
 return axes

def mli(x,y,q,extension=True):
 x=np.asarray(x,float);y=np.asarray(y,float);q=np.asarray(q,float);axes=independent_axes(x)
 # Exact/constant duplicate coordinates may repeat only with identical labels.
 lut={};nodes=[np.unique(x[:,j]) for j in axes]
 for a,b in zip(x,y):
  k=tuple(a[j] for j in axes)
  if k in lut and not np.array_equal(lut[k],b):raise ValueError('conflicting duplicate node')
  lut[k]=b
 out=[];status=[]
 for a in q:
  brackets=[];outside=False
  for j in range(x.shape[1]):
   if j in axes:continue
   if np.ptp(x[:,j])<=1e-14:outside|=bool(abs(a[j]-x[0,j])>1e-12)
   else:
    for k in axes:
     if np.allclose(x[:,j],x[:,k],rtol=0,atol=1e-14):outside|=bool(abs(a[j]-a[k])>1e-12);break
  for j,ns in zip(axes,nodes):
   outside|=bool(a[j]<ns[0] or a[j]>ns[-1]);z=float(np.clip(a[j],ns[0],ns[-1]));i=np.searchsorted(ns,z)
   if i<len(ns) and ns[i]==z:brackets.append([(float(ns[i]),1.)])
   else:
    lo,hi=ns[i-1],ns[i];t=(z-lo)/(hi-lo);brackets.append([(float(lo),1-t),(float(hi),t)])
  corners=list(itertools.product(*brackets));complete=all(tuple(v[0] for v in c) in lut for c in corners)
  if not complete:
   if not extension:raise ValueError('missing corner')
   # Shared, explicitly specified extension: reuse existing support-only CMI.
   from unified.cmi import multilinear
   from pdkcap.interpolation import predict
   xx=x[:,axes];qq=a[None,axes]
   floor=predict(x,y,a[None],'linear')[0]
   val=multilinear(xx,y,qq,len(axes),floor)[0][0] if axes else y[0]
   tag='sparse_support_extension'
  else:
   val=sum((np.prod([v[1] for v in c])*lut[tuple(v[0] for v in c)] for c in corners),start=np.zeros(y.shape[1]));tag='explicit_clamp' if outside else 'complete_cell'
  out.append(val);status.append(tag)
 return np.asarray(out),status

def width_index(widths,w,unit=4):
 widths=np.asarray(widths,int)
 if w>=widths[-1]:return len(widths)-1
 if w<widths[0]:return 0
 mp={}
 for j in range(len(widths)-1):
  for z in range(int(widths[j]),int(widths[j+1])+1,unit):
   if z<widths[-1]:mp[(z-widths[0])//unit]=j
 return mp[(int(w)-widths[0])//unit]

def grid(x,y,unit=4):
 x=np.asarray(x,int);y=np.asarray(y,float)
 if len(x)<2 or np.any(np.diff(x)<=0):raise ValueError('non-distinct quantized separation')
 g={}
 for i in range(len(x)-1):
  for d in range(int(x[i]),int(x[i+1])+1,unit):g[d//unit]=(d,y[i]+(y[i+1]-y[i])*(d-x[i])/(x[i+1]-x[i]))
 return g

def openrcx(x,y,q,scale=1000.,quantized=True,override=None):
 x=np.asarray(x,float);y=np.asarray(y,float);q=np.asarray(q,float)
 ws=np.unique(x[:,0]);wi=np.floor(ws*scale+.5).astype(int)
 if len(np.unique(wi))!=len(wi):raise ValueError('quantized width collision')
 slices={};out=[];meta=[]
 for j,w in enumerate(ws):
  ids=np.flatnonzero(x[:,0]==w);ids=ids[np.argsort(x[ids,1])];ds=np.floor(x[ids,1]*scale+.5).astype(int)
  if len(ds)==1:slices[j]=(ids,ds,{})
  else:slices[j]=(ids,ds,grid(ds,y[ids]))
 for a in q:
  wr,dr=np.floor(a[:2]*scale+.5).astype(int);j=width_index(wi,wr);ids,ds,g=slices[j]
  if not quantized:
   z=np.array([np.interp(a[1],x[ids,1],y[ids,k]) for k in range(y.shape[1])]);eff=float(a[1]);path='ideal_distance'
  elif dr<=ds[0] or len(ds)==1:z=y[ids[0]];eff=int(ds[0]);path='measure_first'
  elif dr>=ds[-1]-4 and ds[-1]>0:z=y[ids[-1]];eff=int(ds[-1]);path='measure_last'
  else:
   eff,z=g[dr//4];path='compute'
   if override is not None and (j,dr//4) in override:z=override[j,dr//4];path='injected'
  out.append(z);meta.append(dict(width_index=j,mapped_width_um=float(ws[j]),effective_separation=eff,path=path,slot=int(dr//4)))
 return np.asarray(out),meta

def multilinear_cell(vertices, fractions, dtype=np.float64):
 """Explicit 2^d corner API, bit j chooses high endpoint on axis j.
 This primitive preserves requested arithmetic precision; public experiments use
 float64. Repeated/constant axes are removed before constructing a cell.
 """
 v=np.asarray(vertices,dtype=dtype);t=np.asarray(fractions,dtype=dtype)
 if len(v)!=1<<len(t):raise ValueError('one vector per binary-ordered vertex required')
 out=np.zeros(v.shape[1:],dtype=dtype)
 for mask in range(len(v)):
  w=dtype(1)
  for j in range(len(t)):w=dtype(w*(t[j] if (mask>>j)&1 else dtype(1)-t[j]))
  out+=w*v[mask]
 return out
