"""Cheap risk routing before expensive experts, with per-component decisions."""
import numpy as np
import torch
from torch import nn


class RiskRouter(nn.Module):
    def __init__(self, features, experts, targets):
        super().__init__(); self.experts = experts; self.targets = targets
        self.network = nn.Sequential(nn.Linear(features, 32), nn.ReLU(), nn.Linear(32, 32), nn.ReLU(), nn.Linear(32, experts*targets))

    def forward(self, features):
        return self.network(features).reshape(-1, self.experts, self.targets)


def choose(risk, valid, mixture=False, ambiguity=.1):
    """Risk is [queries,experts,targets]; invalid predictions never enter mixing."""
    risk = np.asarray(risk, float); valid = np.asarray(valid, bool)
    if risk.ndim != 3 or valid.shape != risk.shape[:2]: raise ValueError('unaligned routing risks')
    if not valid.any(axis=1).all(): raise ValueError('no applicable expert')
    if not np.isfinite(risk).all() or (risk < 0).any(): raise ValueError('invalid predicted risk')
    masked = np.where(valid[:, :, None], risk, np.inf)
    order = np.argsort(masked, axis=1, kind='stable')
    first = order[:, 0]; second = order[:, min(1, risk.shape[1]-1)]
    q, t = np.indices(first.shape)
    one, two = masked[q, first, t], masked[q, second, t]
    mix = np.zeros_like(one)
    if mixture:
        eligible = np.isfinite(two) & (second != first) & (two <= (1+ambiguity)*np.maximum(one, 1e-12))
        mix[eligible] = one[eligible]/np.maximum(one[eligible]+two[eligible], 1e-12)
        # Both risks exactly zero: deterministic equal mixture of distinct experts.
        mix[eligible & (one == 0) & (two == 0)] = .5
    return first, second, mix


def combine(predictions, first, second, second_weight):
    """Gather only chosen experts so unused NaN slots cannot contaminate output."""
    p = np.asarray(predictions); q, t = np.indices(first.shape)
    output = p[first, q, t].copy()
    mixed = second_weight > 0
    output[mixed] = ((1-second_weight[mixed])*output[mixed]
        +second_weight[mixed]*p[second[mixed], q[mixed], t[mixed]])
    if not np.isfinite(output).all(): raise ValueError('selected expert was not computed or valid')
    return output


def infer(experts, table, observed, values, risk, names, mixture=False, diagnostics=False):
    prepared = experts.support(table, observed, values)
    valid = experts.valid(table, prepared, names).T
    first, second, weight = choose(risk, valid, mixture=mixture)
    used = sorted(set(first.ravel()) | set(second[weight > 0].ravel()))
    selected = [names[i] for i in used]
    result = experts.all(table, observed, values, selected)
    all_predictions = np.full((len(names), len(table['coordinates']), np.asarray(values).shape[1]), np.nan)
    all_predictions[used] = result['predictions']
    output = combine(all_predictions, first, second, weight)
    output[np.asarray(observed, int)] = values
    if diagnostics:
        return dict(prediction=output, first=first, second=second, second_weight=weight,
            experts_computed=selected, segment=prepared['support']['segment'])
    return output
