"""Episode encoding: one label-blind pass that produces every tensor the
unified network consumes.

Token features and the anchor are produced exactly as in the frozen Round-3
batch preparation (`pdkcap.round3_batch.prepare`), so a trunk trained here is
drop-in comparable with the frozen one; the support partition, the classical
correction basis and the clamp envelope come from the same single `describe`
call so no support statistic is computed twice.
"""
import numpy as np

from .basis import CLASSICAL, context_vector, support_state
from .workspace import archive_on_path

archive_on_path()

from pdkcap.round3_support import describe  # noqa: E402

RATIOS = (.1, .3, .5, .7)


def encode(table, observed, values, scales, names=CLASSICAL):
    """One `describe` call, then both the token stream and the basis."""
    x = np.asarray(table['coordinates'], float)
    observed = np.asarray(observed, int)
    values = np.asarray(values, float)
    ys = np.asarray(scales['targets'][table['family']], float)
    xs = np.asarray(scales['coordinates'], float)
    state = support_state(table, observed, values, ys, names)

    encoded = np.zeros((len(x), len(ys)))
    encoded[observed] = values / ys
    present = np.zeros((len(x), 1))
    present[observed] = 1.
    context = context_vector(table)
    anchor_scaled = state['anchor'] / ys
    features = np.concatenate([np.log1p(x / xs), np.tile(context, (len(x), 1)), encoded,
                               present, anchor_scaled, np.tile([1., 0.], (len(x), 1))], axis=1)
    material_tokens = []
    for region in table.get('materials') or []:
        token = np.zeros(features.shape[1])
        token[:3] = [np.log1p(region['bottom'] / xs[0]), np.log1p(region['top'] / xs[0]),
                     np.log1p(region['er'])]
        token[3:14] = context
        token[-2:] = [0., 1.]
        material_tokens.append(token)
    anchor_tokens = anchor_scaled
    if material_tokens:
        features = np.concatenate([features, np.asarray(material_tokens)])
        anchor_tokens = np.concatenate([anchor_scaled, np.zeros((len(material_tokens), len(ys)))])
    gate = np.zeros((len(features), state['gate'].shape[1]))
    gate[:len(x)] = state['gate']
    geometry = state['geometry']
    count = len(features)
    lower = np.zeros((count, len(ys)))
    upper = np.zeros((count, len(ys)))
    inside = np.zeros(count, bool)
    lower[:len(x)] = geometry['lower'] / ys[None, :]
    upper[:len(x)] = geometry['upper'] / ys[None, :]
    inside[:len(x)] = geometry['inside']
    if not np.isfinite(features).all():
        raise ValueError('nonfinite token features')
    if not np.isfinite(state['delta'][state['valid']] / ys[None, :]).all():
        raise ValueError('nonfinite scaled correction basis')
    return dict(
        table_id=table['table_id'],
        n=len(x), targets=len(ys),
        features=features.astype('float32'),
        anchor=anchor_tokens.astype('float32'),
        gate=gate.astype('float32'),
        delta=(state['delta'] / ys[None, None, :]).astype('float32'),
        valid=state['valid'],
        lower=lower.astype('float32'), upper=upper.astype('float32'), inside=inside,
        segment=state['segment'], observed=observed, values=values, scales=ys,
        basis_names=state['names'])


def stack(rows, device='cpu'):
    """Pad a list of encoded episodes into one batch."""
    import torch
    if not rows:
        raise ValueError('empty batch')
    width = rows[0]['features'].shape[1]
    gate_width = rows[0]['gate'].shape[1]
    experts = rows[0]['delta'].shape[0]
    targets = rows[0]['targets']
    for row in rows:
        if (row['features'].shape[1] != width or row['gate'].shape[1] != gate_width
                or row['delta'].shape[0] != experts or row['targets'] != targets):
            raise ValueError('ragged episode batch')
    length = max(len(row['features']) for row in rows)
    batch = len(rows)
    features = np.zeros((batch, length, width), 'float32')
    anchor = np.zeros((batch, length, targets), 'float32')
    gate = np.zeros((batch, length, gate_width), 'float32')
    delta = np.zeros((batch, length, experts, targets), 'float32')
    valid = np.zeros((batch, length, experts), bool)
    lower = np.zeros((batch, length, targets), 'float32')
    upper = np.zeros((batch, length, targets), 'float32')
    inside = np.zeros((batch, length), bool)
    padding = np.ones((batch, length), bool)
    for index, row in enumerate(rows):
        n = len(row['features'])
        points = row['delta'].shape[1]
        if points > n:
            raise ValueError('correction basis longer than the token stream')
        features[index, :n] = row['features']
        anchor[index, :n] = row['anchor']
        gate[index, :n] = row['gate']
        # The basis covers geometry tokens only; appended material tokens keep
        # their initialised zeros, which the model reads as an empty basis.
        delta[index, :points] = row['delta'].transpose(1, 0, 2)
        valid[index, :points] = row['valid'].T
        lower[index, :n] = row['lower']
        upper[index, :n] = row['upper']
        inside[index, :n] = row['inside']
        padding[index, :n] = False
    def to(array):
        return torch.as_tensor(array).to(device)

    return dict(features=to(features), anchor=to(anchor), gate=to(gate), delta=to(delta),
                valid=to(valid), lower=to(lower), upper=to(upper), inside=to(inside),
                padding=to(padding), rows=rows)
