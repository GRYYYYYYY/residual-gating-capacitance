"""Validation-frozen segment experts, scored on equal populations with linear fallback."""
import numpy as np
from .round3_support import SEGMENTS
from .round3_router import infer


def select_segments(records, names):
    """Records carry query predictions [Q,E,T] and training-only scales.

    An inapplicable expert is evaluated with its actual deployment fallback,
    linear, so an expert cannot win by skipping difficult validation queries.
    The caller supplies table/protocol/episode balanced weights per query.
    """
    names = list(names)
    if len(set(names)) != len(names) or 'linear' not in names:
        raise ValueError('unique experts and linear fallback required')
    linear = names.index('linear')
    totals = None
    weights = np.zeros(len(SEGMENTS))
    coverage = np.zeros((len(SEGMENTS), len(names)))
    for row in records:
        if row['partition'] != 'val':
            raise ValueError('selection accepts validation records only')
        truth = np.asarray(row['truth'], float)
        predictions = np.asarray(row['prediction'], float)
        valid = np.asarray(row['valid'], bool)
        segment = np.asarray(row['segment'], int)
        weight = np.asarray(row['weight'], float)
        scale = np.asarray(row['scale'], float)
        if truth.ndim != 2:
            raise ValueError('query by target truth required')
        q, targets = truth.shape
        if predictions.shape != (q,len(names),targets) or valid.shape != (q,len(names)):
            raise ValueError('unaligned expert predictions')
        if segment.shape != (q,) or weight.shape != (q,) or scale.shape != (targets,):
            raise ValueError('unaligned selection metadata')
        if (segment<0).any() or (segment>=len(SEGMENTS)).any():
            raise ValueError('unknown support segment')
        if not valid[:,linear].all() or (scale<=0).any() or (weight<=0).any():
            raise ValueError('invalid fallback, scales or weights')
        if not all(np.isfinite(x).all() for x in (truth, scale, weight, predictions[valid])):
            raise ValueError('nonfinite valid selection inputs')
        deployed = np.where(valid[:,:,None], predictions, predictions[:,linear:linear+1,:])
        error = ((deployed-truth[:,None,:])/scale)**2
        if totals is None:
            totals = np.zeros((len(SEGMENTS),len(names),targets))
        if totals.shape[2] != targets:
            raise ValueError('inconsistent target dimensions')
        for s in range(len(SEGMENTS)):
            take = segment == s
            totals[s] += np.sum(error[take]*weight[take,None,None], axis=0)
            weights[s] += weight[take].sum()
            coverage[s] += np.sum(valid[take]*weight[take,None], axis=0)
    if totals is None:
        raise ValueError('empty validation population')
    selected = []
    evidence = []
    for s in range(len(SEGMENTS)):
        if weights[s] == 0:
            selected.append([linear]*totals.shape[2])
            evidence.append(dict(segment=SEGMENTS[s], status='no_validation_evidence', scores=None, coverage=None))
        else:
            scores = totals[s]/weights[s]
            selected.append(np.argmin(scores,axis=0).tolist())
            evidence.append(dict(segment=SEGMENTS[s], status='selected', normalized_mse=scores.tolist(),
                coverage=(coverage[s]/weights[s]).tolist(), weight=float(weights[s])))
    return dict(version='round3-fixed-segment-v1', expert_names=names, selected=selected,
        fallback='linear', evidence=evidence,
        selection_metric='weighted training-scale normalized MSE; invalid expert uses linear on the same queries')


class SegmentPredictor:
    def __init__(self, experts, selection):
        if selection['version'] != 'round3-fixed-segment-v1':
            raise ValueError('unknown segment selector version')
        self.experts = experts
        self.names = selection['expert_names']
        self.selected = np.asarray(selection['selected'], int)
        if self.selected.ndim != 2 or self.selected.shape[0] != len(SEGMENTS):
            raise ValueError('invalid segment selection shape')
        if (self.selected<0).any() or (self.selected>=len(self.names)).any():
            raise ValueError('invalid selected expert')
        self.linear = self.names.index('linear')

    def predict(self, table, observed, values, diagnostics=False):
        prepared = self.experts.support(table, observed, values)
        if np.asarray(values).shape[1] != self.selected.shape[1]:
            raise ValueError('target dimension mismatch')
        chosen = self.selected[prepared['support']['segment']]
        # Validity masking excludes an unavailable selected expert; linear wins next.
        risk = np.full((prepared['n'],len(self.names),self.selected.shape[1]), 2.)
        risk[:,self.linear,:] = 1.
        q,t = np.indices(chosen.shape)
        risk[q,chosen,t] = 0.
        return infer(self.experts,table,observed,values,risk,self.names,diagnostics=diagnostics)
