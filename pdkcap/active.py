"""Paired adaptive-query evaluation with immutable scoring population."""
import argparse,collections,json,time
from pathlib import Path
import numpy as np
import torch
from .common import read_tables,write_json,file_hash,digest
from .sampling import QueryOracle,geometry_order,select
from .model import ConditionalModel,predict_model
from .interpolation import predict
from .metrics import record,summarize
from .train import unique_tables


def fixed_population(table,seed):
    n=len(table['coordinates'])
    if n<8:raise ValueError('active evaluation needs >=8 points')
    # Same evaluation/candidate populations for every strategy and budget.
    rng=np.random.default_rng(seed)
    evaluation=np.sort(rng.choice(n,max(2,round(.2*n)),replace=False))
    candidates=np.setdiff1d(np.arange(n),evaluation)
    initial=geometry_order(table['coordinates'],candidates)[:4]
    return candidates,evaluation,initial


def run(table,strategy,budgets,seed,models=(),scales=None,predictor='linear'):
    x=np.asarray(table['coordinates'],float);candidates,evaluation,initial=fixed_population(table,seed)
    budgets=[b for b in budgets if 4<=b<=len(candidates)]
    if not budgets:return dict(records=[],history=[],reason='insufficient candidate population')
    oracle=QueryOracle(table['labels'],candidates,max(budgets));history=[];records=[]
    for i in initial:oracle.query(i);history.append(int(i))
    training_scale=np.asarray(scales['targets'][table['family']]) if scales is not None else None
    prediction_seconds=0.;selection_seconds=0.
    while True:
        observed,values=oracle.observations
        prediction_start=time.perf_counter()
        interp,_=predict(x[observed],values,x,'linear')
        need_models=predictor=='model' or strategy in ('learned','disagreement_only','residual_only')
        predictions=np.array([predict_model(model,table,observed,values,scales) for model in models]) if models and need_models else None
        if predictor=='linear':pred=interp
        elif predictor=='model' and models:pred=predictions.mean(axis=0)
        else:raise ValueError('predictor requires matching model ensemble')
        prediction_seconds+=time.perf_counter()-prediction_start
        if len(observed) in budgets:
            # Evaluator reads sealed values only AFTER predictions and selection state exist.
            records.append(record(table,np.asarray(table['labels'])[evaluation],pred[evaluation],
                strategy=strategy,predictor=predictor,budget=len(observed),seed=seed,
                evaluation_indices=evaluation.tolist(),observation_indices=observed.tolist(),
                prediction_wall_seconds=prediction_seconds,selection_wall_seconds=selection_seconds))
        if len(observed)==max(budgets):break
        scale=training_scale if training_scale is not None else np.maximum(np.sqrt(np.mean(values**2,axis=0)),1e-30)
        selection_start=time.perf_counter()
        index=select(x,candidates,observed,predictions,interp,scale,strategy,seed+len(observed)*997)
        selection_seconds+=time.perf_counter()-selection_start
        oracle.query(index);history.append(int(index))
    return dict(records=records,history=history,evaluation_indices=evaluation.tolist(),candidate_indices=candidates.tolist())


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--partition',choices=['val','test'],default='val')
    p.add_argument('--strategies',nargs='+',default=['random','farthest','curvature'])
    p.add_argument('--budgets',nargs='+',type=int,default=[4,8,16,32,64])
    p.add_argument('--seeds',nargs='+',type=int,default=[11,29,47,71,101])
    p.add_argument('--checkpoints',nargs='*',type=Path,default=[]);p.add_argument('--predictor',choices=['linear','model'],default='linear')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);models=[];scales=None
    for path in a.checkpoints:
        checkpoint=torch.load(path,map_location='cpu',weights_only=True)
        model=ConditionalModel(checkpoint['variant'],targets=checkpoint.get('targets',2));model.load_state_dict(checkpoint['state_dict']);model.eval();models.append(model)
        if scales is not None and scales!=checkpoint['scales']:raise ValueError('ensemble must share frozen training scales')
        scales=checkpoint['scales']
    if set(a.strategies)&{'learned','disagreement_only','residual_only'} and len(models)!=3:raise ValueError('learned acquisition requires three trained seeds')
    tables=unique_tables([t for t in read_tables(a.data) if t['partition']==a.partition]);records=[];traces=[];start=time.perf_counter()
    for t in tables:
        if len(t['coordinates'])<8:continue
        for seed in a.seeds:
            for strategy in a.strategies:
                result=run(t,strategy,a.budgets,seed,models,scales,a.predictor)
                records.extend(result.pop('records'));traces.append(dict(table_id=t['table_id'],strategy=strategy,seed=seed,**result))
    grouped=collections.defaultdict(list)
    for r in records:grouped[(r['strategy'],r['budget'],r['seed'])].append(r)
    summaries=[dict(strategy=s,budget=b,seed=seed,**summarize(rs)) for (s,b,seed),rs in sorted(grouped.items())]
    write_json(a.output/'results.json',dict(partition=a.partition,data_sha256=file_hash(a.data),
        checkpoint_sha256={str(p):file_hash(p) for p in a.checkpoints},predictor=a.predictor,
        records=records,traces=traces,summaries=summaries,elapsed_seconds=time.perf_counter()-start,
        caution='Public-rule queries are simulated, not measured solver or commercial cost.'))
    print(json.dumps(dict(records=len(records),seconds=time.perf_counter()-start)))

if __name__=='__main__':main()
