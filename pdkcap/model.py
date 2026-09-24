"""Support-conditioned Transformer; labels enter ONLY through observed values."""
import numpy as np
import torch
from torch import nn
from .common import FAMILIES
from .interpolation import predict


def fit_scales(tables):
    if not tables or any(t['partition']!='train' for t in tables):
        raise ValueError('scale fitting requires training partition only')
    x=np.concatenate([t['coordinates'] for t in tables]); xs=np.median(np.abs(x),axis=0)
    xs[xs<=0]=1.
    by_family={}
    for family in FAMILIES:
        population=[np.asarray(t['labels']) for t in tables if t['family']==family]
        if not population: raise ValueError(f'no training scale for {family}')
        ys=np.concatenate(population); rms=np.sqrt(np.mean(ys**2,axis=0))
        pooled=max(float(np.sqrt(np.mean(ys**2))),1e-30)
        by_family[family]=np.maximum(rms,pooled*1e-3).tolist()
    return dict(coordinates=xs.tolist(),targets=by_family)


def encode(table, observed, observed_values, scales, baseline_method='linear'):
    x=np.asarray(table['coordinates'],float); observed=np.asarray(observed,int)
    values=np.asarray(observed_values,float)
    if len(observed)!=len(values) or len(set(observed))!=len(observed):
        raise ValueError('support must align with unique indices')
    ys=np.array(scales['targets'][table['family']]); xs=np.array(scales['coordinates'])
    baseline,_=predict(x[observed],values,x,baseline_method)
    encoded=np.zeros((len(x),len(ys)),float); encoded[observed]=values/ys
    present=np.zeros((len(x),1)); present[observed]=1.
    context=[float(table['family']==f) for f in FAMILIES]
    context += [table.get('metal',0)/16,table.get('context_below',0)/16,table.get('context_above',0)/16]
    material=table.get('material_features')
    context += list(material)+[1.] if material is not None else [0.,0.,0.,0.]
    features=np.concatenate([np.log1p(x/xs),np.tile(context,(len(x),1)),
                             encoded,present,baseline/ys,np.tile([1.,0.],(len(x),1))],axis=1)
    material_tokens=[]
    for region in table.get('materials') or []:
        token=np.zeros(features.shape[1])
        token[:3]=[np.log1p(region['bottom']/xs[0]),np.log1p(region['top']/xs[0]),np.log1p(region['er'])]
        token[3:14]=context
        token[-2:]=[0.,1.]
        material_tokens.append(token)
    scaled_baseline=baseline/ys
    if material_tokens:
        features=np.concatenate([features,material_tokens])
        scaled_baseline=np.concatenate([scaled_baseline,np.zeros((len(material_tokens),len(ys)))])
    if not np.isfinite(features).all(): raise ValueError('nonfinite features')
    return torch.tensor(features,dtype=torch.float32),torch.tensor(scaled_baseline,dtype=torch.float32),ys


class ConditionalModel(nn.Module):
    def __init__(self, variant='residual', width=64, layers=2, targets=2):
        super().__init__()
        if variant not in ('direct','residual'): raise ValueError(variant)
        self.variant=variant
        self.targets=targets
        self.input=nn.Linear(17+2*targets,width)
        layer=nn.TransformerEncoderLayer(width,4,dim_feedforward=width*4,
                                          dropout=.1,batch_first=True,norm_first=True)
        self.encoder=nn.TransformerEncoder(layer,layers,enable_nested_tensor=False)
        self.output=nn.Linear(width,targets)
        nn.init.zeros_(self.output.weight)
        nn.init.constant_(self.output.bias,0. if variant=='residual' else 1.)
    def forward(self,features,baseline,padding=None):
        hidden=self.encoder(self.input(features),src_key_padding_mask=padding)
        raw=self.output(hidden)
        return torch.clamp(raw+(baseline if self.variant=='residual' else 0.),min=0.)


def predict_model(model,table,observed,values,scales):
    model.eval()
    f,b,s=encode(table,observed,values,scales)
    device=next(model.parameters()).device
    with torch.no_grad(): pred=model(f[None].to(device),b[None].to(device))[0,:len(table['coordinates'])].cpu().numpy()*s
    pred[observed]=values
    return pred


class GroupDRO:
    def __init__(self,eta=0.,groups=4):
        self.eta=eta; self.weights=np.ones(groups)/groups
    def loss(self,losses):
        # Only currently represented groups update; callers construct balanced batches.
        if set(losses)!=set(range(len(self.weights))):
            raise ValueError('all groups required in each DRO update')
        detached=np.array([float(losses[g].detach()) for g in range(len(self.weights))])
        logits=np.log(np.maximum(self.weights,1e-30))+self.eta*detached
        logits-=logits.max(); self.weights=np.exp(logits); self.weights/=self.weights.sum()
        return sum(float(self.weights[g])*losses[g] for g in losses)
