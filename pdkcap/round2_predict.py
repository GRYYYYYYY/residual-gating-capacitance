"""One prediction adapter shared by fixed, active and OpenRCX export audits."""
import numpy as np
from .common import file_hash
from .interpolation import predict
from .round2_model import load_checkpoint,predict_round2,support_geometry,correct


class Predictors:
    def __init__(self,bundle):
        self.bundle=bundle;self.models={}
        for path,h in bundle.get('checkpoint_hashes',{}).items():
            if file_hash(path)!=h:raise ValueError('checkpoint changed after selection')
        for method in bundle['methods'].values():
            for path in method.get('checkpoints',[]):
                if path not in self.models:self.models[path]=load_checkpoint(path)

    def resolve(self,name):
        return self.bundle['methods'][self.bundle.get('aliases',{}).get(name,name)]

    def all(self,table,observed,values,names=None):
        names=list(names or self.bundle['methods']);x=np.asarray(table['coordinates']);n=len(x)
        cache={};geometries={};out={}
        for name in names:
            config=self.resolve(name)
            if 'classical' in config:
                if config['classical']=='pchip' and table.get('width_count',1)>1:continue
                p,policy=predict(x[observed],values,x,config['classical'])
                out[name]=dict(prediction=p,members=[],diagnostics=dict(policy=policy));continue
            members=[];diagnostics=[]
            for path in config['checkpoints']:
                if path not in cache:
                    model,scales=self.models[path]
                    cache[path]=predict_round2(model,table,observed,values,scales,with_diagnostics=True)
                p,d=cache[path];model,scales=self.models[path]
                key=tuple(scales['targets'][table['family']])
                if key not in geometries:
                    geometries[key]=support_geometry(x[observed],values,x,key,n)
                corrected,cd=correct(p,geometries[key],config.get('correction','none'),config.get('multiplier',1.))
                corrected[observed]=values
                members.append(corrected);diagnostics.append(dict(cd,gates=d['gates']))
            out[name]=dict(prediction=np.mean(members,axis=0),members=members,diagnostics=diagnostics)
        return out
