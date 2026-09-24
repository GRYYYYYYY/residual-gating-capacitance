"""Shared expert outputs for scientific comparisons; not production timing."""
import numpy as np
from .round2_predict import Predictors
from .round3_experts import EXPERTS
from .round3_router import choose, combine


class EvaluationPredictors:
    def __init__(self, deployment):
        self.deployment=deployment
        # Retain original and matched-retraining controls, including bad variants.
        self.controls=Predictors(deployment.bundle['expert_bundle'])

    def all(self,table,observed,values):
        values=np.asarray(values,float);observed=np.asarray(observed,int)
        expert=self.deployment.experts.all(table,observed,values)
        prepared=expert['prepared'];predictions=expert['predictions'];valid=expert['valid'].T
        names=list(EXPERTS);out={};n=len(table['coordinates'])
        for index,name in enumerate(names):
            out[(name,'ensemble' if name in ('original_dro','hard_local','gated_none') else 'classical')]=dict(
                prediction=predictions[index],valid=valid[:,index],routing=None)
        old=self.controls.all(table,observed,values)
        for name,result in old.items():
            seed='ensemble' if result['members'] else 'classical'
            key=(name,seed)
            if key not in out:
                out[key]=dict(prediction=result['prediction'],valid=np.ones(n,bool),routing=None)
            else:
                # Different adapters must preserve existing experts within the
                # previously verified FP32 preparation tolerance.
                scale=np.asarray(self.deployment.experts.scales['targets'][table['family']])
                delta=np.max(np.abs(out[key]['prediction']-result['prediction'])/scale)
                if delta>2e-5:raise ValueError(f'expert adapter drift: {name}: {delta}')
            for seed,prediction in enumerate(result['members']):
                out[(name,str(seed))]=dict(prediction=prediction,valid=np.ones(n,bool),routing=None)
        selected=np.asarray(self.deployment.bundle['fixed_selection']['selected'])[prepared['support']['segment']]
        q,t=np.indices(selected.shape)
        fixed_names=self.deployment.bundle['fixed_selection']['expert_names']
        if fixed_names!=names:raise ValueError('fixed expert ordering mismatch')
        linear=names.index('linear')
        selected=np.where(valid[q,selected],selected,linear)
        fixed=predictions[selected,q,t].copy();fixed[observed]=values
        out[('fixed','deterministic')]=dict(prediction=fixed,valid=np.ones(n,bool),
            routing=dict(first=selected,second=selected,second_weight=np.zeros_like(fixed)))
        for seed in (None,0,1,2):
            router=self.deployment.predictor('risk',seed)
            if tuple(names)!=router.names:raise ValueError('router expert ordering mismatch')
            risk=router.risks(prepared)
            for method in ('risk','top2'):
                first,second,weight=choose(risk,valid,mixture=method=='top2')
                prediction=combine(predictions,first,second,weight);prediction[observed]=values
                out[(method,'ensemble' if seed is None else str(seed))]=dict(prediction=prediction,valid=np.ones(n,bool),
                    routing=dict(first=first,second=second,second_weight=weight))
        selected_method=self.deployment.bundle['selected_method']
        selected_key=(selected_method,'deterministic' if selected_method=='fixed' else 'ensemble')
        out[('round3_selected','selected')]=out[selected_key]
        return dict(methods=out,segment=prepared['support']['segment'],expert_predictions=predictions,
            expert_valid=valid,expert_names=names,scale=np.asarray(self.deployment.experts.scales['targets'][table['family']]),
            interpretation='router seed varies risk model only; expert pool uses three-seed ensemble')
