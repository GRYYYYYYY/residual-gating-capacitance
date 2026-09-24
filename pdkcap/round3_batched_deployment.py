"""Route first, dispatch only used experts, and batch neural work across tables."""
from collections import defaultdict
import numpy as np
from .common import file_hash
from .round2_model import load_checkpoint,correct
from .round3_batch import predict_prepared
from .round3_router import choose,combine


NEURAL={'original_dro','hard_local','gated_none'}


class BatchedDeployment:
    def __init__(self,deployment):
        self.deployment=deployment

    def predict(self,requests,method='selected',seed=None,diagnostics=False):
        """Requests are (table, observed_indices, observed_values); no query truth."""
        if not requests:return []
        deployment=self.deployment;experts=deployment.experts
        if method=='selected':method=deployment.bundle['selected_method']
        if method not in ('fixed','risk','top2'):raise ValueError('unknown routing method')
        if method=='fixed' and seed is not None:raise ValueError('fixed selector has no seed')
        names=deployment.bundle['fixed_selection']['expert_names'];linear=names.index('linear')
        prepared=[experts.support(*request) for request in requests]
        if method!='fixed':
            router=deployment.predictor(method,seed)
            if router.names!=tuple(names):raise ValueError('router expert order mismatch')
            features=[np.c_[p['support']['features'],p['features'][:p['n'],3:14]] for p in prepared]
            all_risks=router.risks_from_features(np.concatenate(features));offset=0
        routes=[];used=[]
        for (table,observed,values),p in zip(requests,prepared):
            valid=experts.valid(table,p,names).T
            if method=='fixed':
                first=deployment.fixed.selected[p['support']['segment']].copy()
                q,t=np.indices(first.shape);first=np.where(valid[q,first],first,linear)
                second=first.copy();weight=np.zeros_like(first,dtype=float)
            else:
                risk=all_risks[offset:offset+p['n']];offset+=p['n']
                first,second,weight=choose(risk,valid,mixture=method=='top2')
            # Known rows are restored exactly. They must not trigger a neural job.
            first[np.asarray(observed,int)]=linear
            second[np.asarray(observed,int)]=linear
            weight[np.asarray(observed,int)]=0.
            selected=sorted(set(first.ravel())|set(second[weight>0].ravel()))
            routes.append((first,second,weight));used.append(selected)
        outputs=[{} for _ in requests];jobs=defaultdict(set)
        for i,((table,observed,values),indices) in enumerate(zip(requests,used)):
            classical=[names[j] for j in indices if names[j] not in NEURAL]
            if classical:
                result=experts.all(table,observed,values,classical)
                outputs[i].update(zip(classical,result['predictions']))
            for j in indices:
                name=names[j]
                if name not in NEURAL:continue
                base='original_dro' if name=='hard_local' else name
                for path in experts.bundle['methods'][base]['checkpoints']:jobs[path].add(i)
        raw={};model_inputs={}
        for path,indices in jobs.items():
            if path not in experts.models:
                if file_hash(path)!=experts.bundle['checkpoint_hashes'][path]:raise ValueError('checkpoint drift')
                experts.models[path]=load_checkpoint(path)
            model,scales=experts.models[path];ordered=sorted(indices)
            inputs=[experts.cache.get(*requests[i],scales) for i in ordered]
            predictions=predict_prepared(model,inputs,batch_size=experts.batch_size,device=experts.device)
            for i,pred,p in zip(ordered,predictions,inputs):raw[path,i]=pred;model_inputs[path,i]=p
        results=[]
        for i,((table,observed,values),indices,route) in enumerate(zip(requests,used,routes)):
            for j in indices:
                name=names[j]
                if name not in NEURAL:continue
                base='original_dro' if name=='hard_local' else name;members=[]
                for path in experts.bundle['methods'][base]['checkpoints']:
                    pred=raw[path,i]
                    if name=='hard_local':
                        pred,_=correct(pred,model_inputs[path,i]['support']['geometry'],'local')
                        pred[np.asarray(observed,int)]=values
                    members.append(pred)
                outputs[i][name]=np.mean(members,axis=0)
            predictions=np.full((len(names),len(table['coordinates']),np.asarray(values).shape[1]),np.nan)
            for name,pred in outputs[i].items():predictions[names.index(name)]=pred
            prediction=combine(predictions,*route);prediction[np.asarray(observed,int)]=values
            if diagnostics:
                results.append(dict(prediction=prediction,first=route[0],second=route[1],second_weight=route[2],
                    experts_computed=[names[j] for j in indices],segment=prepared[i]['support']['segment'],
                    observed_rows='restored via linear slot without scheduling neural experts'))
            else:results.append(prediction)
        return results
