"""Replay router candidates on hash-bound validation predictions, never confirmation."""
import json
from pathlib import Path
import numpy as np
from .common import file_hash
from .round3_router import choose, combine
from .round3_support import SEGMENTS


def records(folder):
    folder=Path(folder)
    receipt=json.loads((folder/'COMPLETED.json').read_text())
    seen=set()
    for shard in receipt['shards']:
        if file_hash(shard['path'])!=shard['sha256'] or file_hash(shard['metadata'])!=shard['metadata_sha256']:
            raise ValueError('validation shard drift')
        meta=json.loads(Path(shard['metadata']).read_text())
        if meta['partition']!='val':raise ValueError('nonvalidation record')
        if meta['table_id'] in seen:raise ValueError('duplicate validation table')
        seen.add(meta['table_id'])
        with np.load(shard['path'],allow_pickle=False) as data:
            row={k:data[k].copy() for k in data.files}
        row.update(partition='val',table_id=meta['table_id'],process=meta['process'],family=meta['family'])
        yield row


def fixed_predictions(row,selection):
    names=selection['expert_names'];linear=names.index('linear')
    selected=np.asarray(selection['selected'],int)[row['segment']]
    q,t=np.indices(selected.shape)
    chosen=np.where(row['valid'][q,selected],selected,linear)
    output=row['prediction'][q,chosen,t]
    if not np.isfinite(output).all():raise ValueError('invalid deployed fixed prediction')
    return output


def score(folder,selection,router=None,mixture=False):
    """Weighted per-segment/target RMSE, plus all-query normalized MSE.

    No-evidence segments stay explicit; this is validation selection evidence,
    not the final per-process/family/component confirmation acceptance audit.
    """
    names=json.loads((Path(folder)/'COMPLETED.json').read_text())['expert_names']
    if names!=selection['expert_names'] or (router is not None and tuple(names)!=router.names):
        raise ValueError('expert order mismatch')
    candidate_sse=reference_sse=None
    weights=np.zeros(len(SEGMENTS));total_weight=0.;total_error=0.
    for row in records(folder):
        reference=fixed_predictions(row,selection)
        if router is None:
            predicted=reference
        else:
            risk=router.risks_from_features(row['features'])
            first,second,mix=choose(risk,row['valid'],mixture=mixture)
            predicted=combine(row['prediction'].transpose(1,0,2),first,second,mix)
        err=((predicted-row['truth'])/row['scale'])**2
        ref=((reference-row['truth'])/row['scale'])**2
        if not np.isfinite(err).all() or not np.isfinite(ref).all():
            raise ValueError('nonfinite validation error')
        if candidate_sse is None:
            candidate_sse=np.zeros((len(SEGMENTS),err.shape[1]));reference_sse=np.zeros_like(candidate_sse)
        for s in range(len(SEGMENTS)):
            take=row['segment']==s;w=row['weight'][take]
            weights[s]+=w.sum()
            candidate_sse[s]+=(err[take]*w[:,None]).sum(axis=0)
            reference_sse[s]+=(ref[take]*w[:,None]).sum(axis=0)
        total_weight+=row['weight'].sum()
        total_error+=(err.mean(axis=1)*row['weight']).sum()
    if total_weight<=0:raise ValueError('empty validation evidence')
    cells=[]
    for s,name in enumerate(SEGMENTS):
        if weights[s]==0:
            cells.append(dict(segment=name,status='no_evidence',passed=None));continue
        candidate=np.sqrt(candidate_sse[s]/weights[s]);reference=np.sqrt(reference_sse[s]/weights[s])
        allowed=np.where(reference<=1e-4,reference+1e-4,reference*1.05)
        cells.append(dict(segment=name,status='scored',candidate_normalized_rmse=candidate.tolist(),
            reference_normalized_rmse=reference.tolist(),allowed=allowed.tolist(),passed=bool((candidate<=allowed).all())))
    return dict(normalized_mse=float(total_error/total_weight),cells=cells,
        supported_segments_passed=all(c['passed'] for c in cells if c['passed'] is not None),
        no_evidence_segments=[c['segment'] for c in cells if c['passed'] is None],
        scope='validation selection only; not full confirmation acceptance')
