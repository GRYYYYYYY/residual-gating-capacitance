"""Shared observed-support preparation and padded, device-resident expert batches."""
from collections import OrderedDict
import numpy as np
import torch
from .common import FAMILIES, digest
from .round2_model import GatedModel, correct
from .round3_support import describe


def prepare(table, observed, values, scales):
    x = np.asarray(table['coordinates'], float); observed = np.asarray(observed, int)
    values = np.asarray(values, float); ys = np.asarray(scales['targets'][table['family']])
    xs = np.asarray(scales['coordinates'])
    support = describe(x, observed, values, ys)
    baseline = support['geometry']['baseline']
    encoded = np.zeros((len(x), len(ys))); encoded[observed] = values/ys
    present = np.zeros((len(x), 1)); present[observed] = 1.
    context = [float(table['family'] == f) for f in FAMILIES]
    context += [table.get('metal', 0)/16, table.get('context_below', 0)/16, table.get('context_above', 0)/16]
    material = table.get('material_features')
    context += list(material)+[1.] if material is not None else [0., 0., 0., 0.]
    features = np.concatenate([np.log1p(x/xs), np.tile(context, (len(x), 1)), encoded,
        present, baseline/ys, np.tile([1., 0.], (len(x), 1))], axis=1)
    tokens = []
    for region in table.get('materials') or []:
        token = np.zeros(features.shape[1])
        token[:3] = [np.log1p(region['bottom']/xs[0]), np.log1p(region['top']/xs[0]), np.log1p(region['er'])]
        token[3:14] = context; token[-2:] = [0., 1.]; tokens.append(token)
    scaled = baseline/ys
    if tokens:
        features = np.concatenate([features, tokens]); scaled = np.concatenate([scaled, np.zeros((len(tokens), len(ys)))])
    gate = np.zeros((len(features), 4+len(ys))); gate[:len(x)] = support['geometry']['features']
    if not np.isfinite(features).all(): raise ValueError('nonfinite features')
    return dict(features=features.astype('float32'), baseline=scaled.astype('float32'),
        gate=gate.astype('float32'), scales=ys, support=support, n=len(x),
        observed=observed.copy(), values=values.copy())


class SupportCache:
    """Bounded LRU; only known input fields are hashed, never hidden labels."""
    def __init__(self, capacity=128):
        if capacity < 1: raise ValueError('positive cache capacity required')
        self.capacity = capacity; self.cache = OrderedDict(); self.hits = 0; self.misses = 0

    def get(self, table, observed, values, scales):
        payload = {k: table.get(k) for k in ('coordinates', 'family', 'metal', 'context_below', 'context_above', 'material_features', 'materials')}
        key = digest(dict(table=payload, observed=np.asarray(observed).tolist(), values=np.asarray(values).tolist(), scales=scales, version='round3-batch-v1'))
        if key in self.cache:
            self.hits += 1; self.cache.move_to_end(key); return self.cache[key]
        result = prepare(table, observed, values, scales); self.misses += 1; self.cache[key] = result
        if len(self.cache) > self.capacity: self.cache.popitem(last=False)
        return result


def predict_prepared(model, prepared, batch_size=32, device='cpu', correction='none', diagnostics=False):
    """A model returns one array per table; batch changes cannot change support.

    Bucket by actual token count, padding only inside a bucket batch. All model
    outputs return in original table order. No GPU auto-detection or fallback.
    """
    if batch_size < 1: raise ValueError('positive batch size required')
    device = torch.device(device); model.to(device); model.eval()
    order = sorted(range(len(prepared)), key=lambda i: len(prepared[i]['features']))
    result = [None]*len(prepared)
    with torch.inference_mode():
        for start in range(0, len(order), batch_size):
            indices = order[start:start+batch_size]; rows = [prepared[i] for i in indices]
            length = max(len(r['features']) for r in rows)
            f = np.zeros((len(rows), length, rows[0]['features'].shape[1]), dtype='float32')
            b = np.zeros((len(rows), length, len(rows[0]['scales'])), dtype='float32')
            g = np.zeros((len(rows), length, rows[0]['gate'].shape[1]), dtype='float32')
            padding = np.ones((len(rows), length), dtype=bool)
            for j, r in enumerate(rows):
                n = len(r['features']); f[j, :n] = r['features']; b[j, :n] = r['baseline']; g[j, :n] = r['gate']; padding[j, :n] = False
            tf = torch.from_numpy(f).to(device); tb = torch.from_numpy(b).to(device); mask = torch.from_numpy(padding).to(device)
            weights = None
            if isinstance(model, GatedModel):
                tg = torch.from_numpy(g).to(device)
                if diagnostics:
                    prediction, weights = model(tf, tb, padding=mask, geometry=tg, return_gate=True)
                    weights = weights.cpu().numpy()
                else: prediction = model(tf, tb, padding=mask, geometry=tg)
            else: prediction = model(tf, tb, padding=mask)
            prediction = prediction.cpu().numpy()
            for j, (index, row) in enumerate(zip(indices, rows)):
                p = prediction[j, :row['n']]*row['scales']
                p, info = correct(p, row['support']['geometry'], correction)
                p[row['observed']] = row['values']
                if diagnostics:
                    info['gates'] = weights[j, :row['n']] if weights is not None else None
                    result[index] = dict(prediction=p, diagnostics=info)
                else: result[index] = p
    return result
