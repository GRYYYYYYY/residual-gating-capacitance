"""Observed-only geometry, explicit local constraints, and trainable residual gates."""
import numpy as np
import torch
from torch import nn
from scipy.spatial import Delaunay, QhullError
from scipy.spatial.distance import cdist
from .interpolation import predict, reduce_coordinates
from .model import ConditionalModel, encode

CORRECTIONS = ('none', 'local', 'boundary', 'both')


def support_geometry(x, values, query, target_scales, total_count=None):
    x=np.asarray(x,float); y=np.asarray(values,float); q=np.asarray(query,float)
    scales=np.asarray(target_scales,float)
    baseline,policy=predict(x,y,q,'linear')  # also validates duplicate observations
    x, indices=np.unique(x,axis=0,return_index=True);y=y[indices]
    a,b,axes=reduce_coordinates(x,q)
    origin=x.min(axis=0); span=np.ptp(x,axis=0); span[span==0]=1.
    full=(x-origin)/span; fullq=(q-origin)/span
    distances=cdist(fullq,full); nearest=distances.argmin(axis=1)
    lo=y[nearest].copy();hi=lo.copy();local_span=np.zeros(len(q)); inside=np.zeros(len(q),bool)
    # Queries outside the observed affine subspace are outside support, even
    # when the independent-axis projection happens to lie inside its interval.
    if axes:
        affine=np.linalg.lstsq(np.c_[a,np.ones(len(a))],full,rcond=None)[0]
        on_span=np.max(np.abs(np.c_[b,np.ones(len(b))]@affine-fullq),axis=1)<=1e-9
    else:on_span=np.max(np.abs(fullq-full[0]),axis=1)<=1e-9
    vertices=[None]*len(q);fallback=None
    if not axes:
        inside=on_span
        for i in np.flatnonzero(inside):vertices[i]=np.array([0])
        fallback='constant-degenerate'
    elif len(axes)==1:
        order=np.argsort(a[:,0]);aa=a[order,0]
        inside=on_span & (b[:,0]>=aa[0]) & (b[:,0]<=aa[-1])
        for i in np.flatnonzero(inside):
            right=min(max(int(np.searchsorted(aa,b[i,0],side='right')),1),len(aa)-1)
            vertices[i]=order[[right-1,right]]
    else:
        try:
            triangulation=Delaunay(a);simplices=triangulation.find_simplex(b)
            inside=on_span & (simplices>=0)
            for i in np.flatnonzero(inside):vertices[i]=triangulation.simplices[simplices[i]]
        except QhullError:fallback='nearest-degenerate-hull'
    for i,v in enumerate(vertices):
        if v is not None:
            lo[i]=y[v].min(axis=0);hi[i]=y[v].max(axis=0)
            local_span[i]=np.linalg.norm(np.ptp(full[v],axis=0))
    # For rank-deficient outside points, the boundary rule is nearest observed.
    boundary=baseline.copy();boundary[~inside]=y[nearest[~inside]]
    features=np.column_stack([np.full(len(q),len(x)/(total_count or len(q))),
        np.log1p(distances.min(axis=1)),np.log1p(local_span),inside.astype(float),
        np.log1p(np.maximum(hi-lo,0)/scales)])
    return dict(features=features,lower=lo,upper=hi,inside=inside,boundary=boundary,
                baseline=baseline,policy=policy,fallback=fallback,axes=axes)


def correct(prediction,geometry,correction='none',multiplier=1.):
    if correction not in CORRECTIONS:raise ValueError(correction)
    b=geometry['baseline'];p=np.maximum(0,b+float(multiplier)*(np.asarray(prediction)-b))
    before=p.copy();inside=geometry['inside']
    if correction in ('local','both'):
        p[inside]=np.clip(p[inside],geometry['lower'][inside],geometry['upper'][inside])
    clipped=np.any(p!=before,axis=1)
    fallback=np.zeros(len(p),bool)
    if correction in ('boundary','both'):
        fallback=~inside;p[fallback]=geometry['boundary'][fallback]
    return p,dict(clamped=clipped,boundary_fallback=fallback,inside=inside)


class GatedModel(ConditionalModel):
    version='gated-residual-v1'
    def __init__(self,targets=2,width=64,layers=2):
        super().__init__('residual',width,layers,targets)
        self.gate=nn.Sequential(nn.Linear(width+4+targets,32),nn.ReLU(),nn.Linear(32,targets))
        nn.init.zeros_(self.gate[-1].weight);nn.init.zeros_(self.gate[-1].bias)

    def forward(self,features,baseline,padding=None,geometry=None,return_gate=False):
        if geometry is None:raise ValueError('observed-only gate geometry is required')
        hidden=self.encoder(self.input(features),src_key_padding_mask=padding)
        weight=torch.sigmoid(self.gate(torch.cat([hidden,geometry],dim=-1)))
        prediction=torch.clamp(baseline+weight*self.output(hidden),min=0.)
        return (prediction,weight) if return_gate else prediction


def inputs(table,observed,values,scales):
    f,b,s=encode(table,observed,values,scales)
    x=np.asarray(table['coordinates'],float)
    g=support_geometry(x[observed],values,x,s,total_count=len(x))
    gate=np.zeros((len(f),4+len(s)),float);gate[:len(x)]=g['features']
    return f,b,s,torch.tensor(gate,dtype=torch.float32),g


def load_checkpoint(path):
    c=torch.load(path,map_location='cpu',weights_only=True)
    model=GatedModel(c.get('targets',2)) if c.get('model_version')==GatedModel.version else ConditionalModel(c['variant'],targets=c.get('targets',2))
    model.load_state_dict(c['state_dict']);model.eval()
    return model,c['scales']


def predict_round2(model,table,observed,values,scales,correction='none',multiplier=1.,with_diagnostics=False):
    f,b,s,g,geometry=inputs(table,observed,values,scales);model.eval()
    device=next(model.parameters()).device;n=len(table['coordinates'])
    with torch.no_grad():
        if isinstance(model,GatedModel):
            p,weight=model(f[None].to(device),b[None].to(device),geometry=g[None].to(device),return_gate=True)
            weights=weight[0,:n].cpu().numpy()
        else:
            p=model(f[None].to(device),b[None].to(device));weights=None
        p=p[0,:n].cpu().numpy()*s
    p,diagnostics=correct(p,geometry,correction,multiplier)
    p[np.asarray(observed,int)]=values
    diagnostics.update(gates=weights,geometry_policy=geometry['policy'],geometry_fallback=geometry['fallback'])
    return (p,diagnostics) if with_diagnostics else p
