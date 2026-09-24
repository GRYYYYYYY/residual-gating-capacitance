"""Lazy expert adapter: absent experts are invalid, not fabricated predictions."""
import numpy as np
from scipy.spatial.distance import cdist
from .common import file_hash
from .interpolation import predict, reduce_coordinates
from .round2_model import load_checkpoint
from .round3_batch import SupportCache, predict_prepared

GP_CONFIGS = {f'gp_l{length:g}_r{ridge:g}': (length, ridge)
              for length in (.5, 1., 2.) for ridge in (1e-6, 1e-4)}
EXPERTS = ('linear', 'pchip', 'width_linear', *GP_CONFIGS, 'original_dro', 'hard_local', 'gated_none')


def gaussian_process(x, y, query, length_multiplier=1., ridge=1e-6):
    x, y, q = np.asarray(x, float), np.asarray(y, float), np.asarray(query, float)
    if length_multiplier <= 0 or ridge <= 0: raise ValueError('invalid GP parameters')
    ux, indices, inverse = np.unique(x, axis=0, return_index=True, return_inverse=True)
    if not np.array_equal(y, y[indices][inverse]): raise ValueError('conflicting duplicate observations')
    x, y = ux, y[indices]
    a, b, axes = reduce_coordinates(x, q)
    if not axes: out = np.repeat(y[:1], len(q), axis=0)
    else:
        dd = cdist(a, a); positive = dd[dd > 0]
        length = (np.median(positive) if len(positive) else 1.)*length_multiplier
        kernel = np.exp(-.5*(dd/length)**2)+ridge*np.eye(len(a))
        mean = y.mean(axis=0)
        out = mean+np.exp(-.5*(cdist(b, a)/length)**2)@np.linalg.solve(kernel, y-mean)
    out = np.maximum(out, 0.)
    for i, point in enumerate(q):
        exact = np.flatnonzero(np.all(x == point, axis=1))
        if len(exact): out[i] = y[exact[0]]
    return out


class Experts:
    def __init__(self, bundle, routing_scales, device='cpu', batch_size=32):
        self.bundle = bundle; self.scales = routing_scales; self.device = device
        self.batch_size = batch_size; self.cache = SupportCache(); self.models = {}

    def support(self, table, observed, values):
        return self.cache.get(table, observed, values, self.scales)

    def valid(self, table, prepared, names=EXPERTS):
        valid = np.ones((len(names), prepared['n']), bool)
        for j, name in enumerate(names):
            if name == 'width_linear': valid[j] = prepared['support']['width_valid']
            elif name == 'pchip': valid[j] = table.get('width_count', 1) == 1
            elif name not in EXPERTS: raise ValueError('unknown expert')
        return valid

    def all(self, table, observed, values, names=EXPERTS):
        if len(set(names)) != len(names): raise ValueError('duplicate expert names')
        prepared = self.support(table, observed, values); valid = self.valid(table, prepared, names)
        x = np.asarray(table['coordinates'], float); o = np.asarray(observed, int); y = np.asarray(values, float)
        predictions = np.full((len(names), len(x), y.shape[1]), np.nan)
        neural_cache = {}
        for j, name in enumerate(names):
            if not valid[j].any(): continue
            if name == 'linear': p = prepared['support']['geometry']['baseline'].copy()
            elif name == 'width_linear': p = prepared['support']['width_prediction'].copy()
            elif name == 'pchip': p, _ = predict(x[o], y, x, 'pchip')
            elif name in GP_CONFIGS: p = gaussian_process(x[o], y, x, *GP_CONFIGS[name])
            else:
                base = 'original_dro' if name == 'hard_local' else name
                config = self.bundle['methods'][base]; members = []
                for path in config['checkpoints']:
                    if path not in self.models:
                        if file_hash(path) != self.bundle['checkpoint_hashes'][path]: raise ValueError('checkpoint hash mismatch')
                        self.models[path] = load_checkpoint(path)
                    model, scales = self.models[path]
                    key = (path, name == 'hard_local')
                    if key not in neural_cache:
                        inputs = self.cache.get(table, observed, values, scales)
                        neural_cache[key] = predict_prepared(model, [inputs], self.batch_size, self.device,
                            correction='local' if name == 'hard_local' else 'none')[0]
                    members.append(neural_cache[key])
                p = np.mean(members, axis=0)
            p[o] = y
            if not np.isfinite(p[valid[j]]).all(): raise ValueError('valid expert returned nonfinite prediction')
            predictions[j] = p
        return dict(predictions=predictions, valid=valid, names=list(names), prepared=prepared)
