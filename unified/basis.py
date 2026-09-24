"""The corrective basis shared by every estimator in this study.

The estimator is written as a residual around one *anchor* interpolation `b`:

    y_hat = clamp0( b + sum_e pi_e * Delta_e ),        Delta_e = f_e - b

so the anchor is the skip path (its own correction is identically zero) and
each expert contributes only the part of its prediction the anchor misses.
Two kinds of basis element exist:

* **frozen classical corrections** -- PCHIP, aligned-width interpolation and the
  RBF-GP family.  They are not learned and carry no parameters; they act as a
  fixed dictionary of local corrections, the same role basis expansions play in
  classical regression.
* **learned corrections** -- the residual head of the network and its locally
  clamped reading.  These need the trunk hidden state, so they are materialised
  inside the model, not here.

Everything in this module is label-blind: only observed indices and observed
values enter, and no hidden query label is ever touched.
"""
import numpy as np

from .workspace import SEGMENTS, archive_on_path

archive_on_path()

from pdkcap.interpolation import predict  # noqa: E402
from pdkcap.round2_model import support_geometry  # noqa: E402
from pdkcap.round3_experts import EXPERTS, GP_CONFIGS, gaussian_process  # noqa: E402
from pdkcap.round3_support import describe  # noqa: E402

# Frozen classical basis, in the frozen expert ordering.  Slot 0 is the anchor
# itself; its correction is defined to be exactly zero rather than recomputed.
CLASSICAL = ('linear', 'pchip', 'width_linear', *GP_CONFIGS)


def segment_slice(targets):
    """Slice of the support features holding the one-hot support region.

    ``round3_support.describe`` emits the geometry block first -- density,
    nearest distance, local span, the inside flag and one envelope ratio *per
    target component* -- and only then the five-way region indicator.  The
    region block therefore starts at ``4 + targets``, and getting this wrong
    silently routes every query by the wrong feature.
    """
    if targets < 1:
        raise ValueError('positive target count required')
    return slice(4 + targets, 9 + targets)
ANCHOR = 0
NEURAL_RAW = 'neural'
NEURAL_CLAMP = 'neural_clamp'
BASIS = CLASSICAL + (NEURAL_RAW, NEURAL_CLAMP)


def context_vector(table):
    """Global structure/material context, identical to the frozen encoder's."""
    vector = [float(table['family'] == name) for name in ('OVER', 'UNDER', 'OVERUNDER', 'DIAGUNDER')]
    vector += [table.get('metal', 0) / 16, table.get('context_below', 0) / 16, table.get('context_above', 0) / 16]
    material = table.get('material_features')
    vector += list(material) + [1.] if material is not None else [0., 0., 0., 0.]
    return np.asarray(vector, float)


def _single_width(table):
    if 'width_count' in table:
        return int(table['width_count']) == 1
    return len(np.unique(np.asarray(table['coordinates'], float)[:, 0])) == 1


def support_state(table, observed, values, target_scales, names=CLASSICAL):
    """Label-blind support description plus the frozen classical correction basis.

    Returns arrays over all ``N`` candidate geometries of the table:

    ``anchor``      [N, K]   the skip path ``b``
    ``delta``       [E, N, K] classical corrections, NaN where inapplicable
    ``valid``       [E, N]   applicability of each classical correction
    ``gate``        [N, G]   routing features, including the support region
    ``geometry``             clamp envelope and inside-support flag for the
                             learned correction
    """
    x = np.asarray(table['coordinates'], float)
    observed = np.asarray(observed, int)
    values = np.asarray(values, float)
    scales = np.asarray(target_scales, float)
    if values.ndim != 2 or values.shape[1] != len(scales):
        raise ValueError('observed values and target scales disagree')
    support = describe(x, observed, values, scales)
    geometry = support['geometry']
    anchor = np.asarray(geometry['baseline'], float)
    if not np.isfinite(anchor).all() or not np.isfinite(scales).all() or (scales <= 0).any():
        raise ValueError('invalid anchor or scales')

    count, targets = len(x), values.shape[1]
    delta = np.full((len(CLASSICAL), count, targets), np.nan)
    valid = np.zeros((len(CLASSICAL), count), bool)
    delta[ANCHOR] = 0.
    valid[ANCHOR] = True

    requested = set(names)
    if 'linear' not in requested:
        raise ValueError('the anchor is not optional: it is the skip path')
    unknown = requested - set(CLASSICAL)
    if unknown:
        raise ValueError(f'unknown basis elements: {sorted(unknown)}')
    for index, name in enumerate(CLASSICAL):
        if index == ANCHOR or name not in requested:
            continue
        if name == 'pchip':
            if not _single_width(table):
                continue
            prediction, _ = predict(x[observed], values, x, 'pchip')
        elif name == 'width_linear':
            if not support['width_valid'].any():
                continue
            prediction = np.asarray(support['width_prediction'], float)
            take = np.asarray(support['width_valid'], bool)
        elif name in GP_CONFIGS:
            prediction = gaussian_process(x[observed], values, x, *GP_CONFIGS[name])
            take = np.ones(count, bool)
        else:
            raise ValueError(f'unknown classical basis element {name}')
        if name != 'width_linear':
            take = np.ones(count, bool)
        take = take & np.isfinite(prediction).all(axis=1)
        delta[index, take] = prediction[take] - anchor[take]
        valid[index, take] = True
    if not valid.any(axis=0).all():
        raise ValueError('anchor must be applicable everywhere')

    features = np.asarray(support['features'], float)
    gate = np.concatenate([features, np.tile(context_vector(table), (count, 1))], axis=1)
    if not np.isfinite(gate).all() or not np.isfinite(delta[valid]).all():
        raise ValueError('nonfinite basis or routing features')
    return dict(anchor=anchor, delta=delta, valid=valid, gate=gate, segment=np.asarray(support['segment'], int),
                geometry=geometry, scales=scales, names=list(CLASSICAL), feature_version='sace-r-support-v1')


def anchor_only(table, observed, values, target_scales):
    """Cheap path used by validation screens that need no correction basis."""
    x = np.asarray(table['coordinates'], float)
    observed = np.asarray(observed, int)
    geometry = support_geometry(x[observed], np.asarray(values, float), x, np.asarray(target_scales, float), total_count=len(x))
    return np.asarray(geometry['baseline'], float), geometry
