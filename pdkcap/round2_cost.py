"""Runtime predictor trained only on recorded old training-layer numerical solves."""
import json
from pathlib import Path
import numpy as np
from .common import ROOT,FAMILIES,read_tables,file_hash,write_json


def features(table):
    x=np.asarray(table['coordinates'],float)
    context=[table.get('metal',0),*table.get('material_features',[0.,0.,0.])]
    return np.c_[np.log1p(x),np.tile(np.log1p(context),(len(x),1)),
                 np.tile([float(table['family']==f) for f in FAMILIES],(len(x),1))]


def cost_arrays(tables,design,run):
    design=Path(design);run=Path(run);summary=json.loads((run/'summary.json').read_text())
    if not summary['all_requested_passed'] or summary['grid_sha256']!=file_hash(design/'grid.json'):
        raise PermissionError('cost replay needs matching complete numerical evidence')
    grid=json.loads((design/'grid.json').read_text());entries={}
    with (run/'ledger.jsonl').open() as f:
        for line in f:
            e=json.loads(line)
            if e['status']!='completed':raise ValueError('incomplete solver record')
            entries[e['id']]=e
    index={}
    for g in grid:
        m=g['spec']['metadata'];coord=(m['width_um'],m['distance_um'],m['lateral_spacing_um'])
        costs={level:float(entries[g['id']+'-'+level]['result']['cpu_seconds']) for level in ('coarse','fine','wide')}
        index[(g['reference_id'],coord)]=dict(fine=costs['fine'],certified=sum(costs.values()))
    return {t['table_id']:{kind:np.array([index[(t['table_id'],tuple(x))][kind] for x in t['coordinates']]) for kind in ('fine','certified')} for t in tables}


def fit(output,source_process=None):
    data=ROOT/'runs/reference_dataset_v2/tables.jsonl'
    tables=[t for t in read_tables(data) if t['partition']=='train' and (source_process is None or t['process_id']==source_process)]
    times=cost_arrays(tables,ROOT/'runs/reference_design_v2',ROOT/'runs/reference_full_v2')
    x=np.concatenate([features(t) for t in tables]);y=np.log(np.concatenate([times[t['table_id']]['certified'] for t in tables]))
    mean=x.mean(axis=0);scale=x.std(axis=0);scale[scale==0]=1.;z=(x-mean)/scale
    target_mean=float(y.mean());coef=np.linalg.solve(z.T@z+np.eye(z.shape[1]),z.T@(y-target_mean))
    model=dict(version='round2-log-runtime-ridge-v1',alpha=1.,mean=mean.tolist(),scale=scale.tolist(),coefficient=coef.tolist(),intercept=target_mean,
        source_process=source_process,training_table_ids=[t['table_id'] for t in tables],training_partition='train',target='sum of coarse/fine/wide solver cpu_seconds',
        data_sha256=file_hash(data),solver_summary_sha256=file_hash(ROOT/'runs/reference_full_v2/summary.json'),
        source_sha256=file_hash(__file__),test_time_access='query geometry only; realized candidate times are never used for selection')
    write_json(output,model);return model


def predict(model,table):
    z=(features(table)-np.asarray(model['mean']))/np.asarray(model['scale'])
    log_time=z@np.asarray(model['coefficient'])+model['intercept']
    return np.exp(np.clip(log_time,-20.,20.))
