"""Label-blind support partitions and a width-preserving classical expert."""
import numpy as np
from scipy.spatial.distance import cdist
from .round2_model import support_geometry

SEGMENTS = ('outside', 'missing_width', 'dense_1d', 'dense_nd', 'sparse_or_degenerate')


def width_linear(x, values, query):
    """Interpolate only exact aligned rows at two bracketing observed widths.

    Unavailable predictions are NaN and accompanied by a false validity mask;
    callers must mask this expert, never replace missing evidence with zero.
    """
    x, y, q = np.asarray(x, float), np.asarray(values, float), np.asarray(query, float)
    if x.ndim != 2 or q.ndim != 2 or y.ndim != 2 or len(x) != len(y) or x.shape[1] != q.shape[1]:
        raise ValueError('unaligned support')
    if not all(np.isfinite(v).all() for v in (x, y, q)):
        raise ValueError('nonfinite support')
    unique, ids, inverse = np.unique(x, axis=0, return_index=True, return_inverse=True)
    if not np.array_equal(y, y[ids][inverse]):
        raise ValueError('conflicting duplicate observations')
    x, y = unique, y[ids]
    out = np.full((len(q), y.shape[1]), np.nan); valid = np.zeros(len(q), bool)
    for i, point in enumerate(q):
        aligned = np.flatnonzero(np.all(x[:, 1:] == point[1:], axis=1))
        exact = aligned[x[aligned, 0] == point[0]]
        if len(exact):
            out[i] = y[exact[0]]; valid[i] = True; continue
        left = aligned[x[aligned, 0] < point[0]]
        right = aligned[x[aligned, 0] > point[0]]
        if not len(left) or not len(right): continue
        lo, hi = left[np.argmax(x[left, 0])], right[np.argmin(x[right, 0])]
        weight = (point[0]-x[lo, 0])/(x[hi, 0]-x[lo, 0])
        out[i] = (1-weight)*y[lo]+weight*y[hi]; valid[i] = True
    return out, valid


def describe(coordinates, observed, values, target_scales, density_multiplier=2.):
    """No table labels or experimental mask names enter this interface."""
    x = np.asarray(coordinates, float); o = np.asarray(observed, int)
    y = np.asarray(values, float); scales = np.asarray(target_scales, float)
    if x.ndim != 2 or not len(o) or len(set(o)) != len(o) or np.any(o < 0) or np.any(o >= len(x)):
        raise ValueError('invalid observed indices')
    if y.ndim != 2 or len(y) != len(o) or scales.shape != (y.shape[1],) or np.any(scales <= 0) or not np.isfinite(scales).all():
        raise ValueError('invalid values/scales')
    g = support_geometry(x[o], y, x, scales, total_count=len(x))
    support = x[o]; span = np.ptp(support, axis=0); span[span == 0] = 1.
    normalized = (support-support.min(axis=0))/span
    queries = (x-support.min(axis=0))/span
    unique = np.unique(normalized, axis=0)
    pair = cdist(unique, unique); np.fill_diagonal(pair, np.inf)
    typical = float(np.median(pair.min(axis=1))) if len(unique) > 1 else 0.
    local_span = np.expm1(g['features'][:, 2])
    dense = (typical > 0) & (local_span <= density_multiplier*typical)
    width_prediction, width_valid = width_linear(support, y, x)
    widths = np.unique(support[:, 0])
    missing_width = (~np.isin(x[:, 0], widths)) & (x[:, 0] > widths.min()) & (x[:, 0] < widths.max())
    rank = len(g['axes'])
    segment = np.full(len(x), 4, dtype=np.int64)
    segment[g['inside'] & dense & (rank == 1)] = 2
    segment[g['inside'] & dense & (rank > 1)] = 3
    segment[g['inside'] & missing_width] = 1
    segment[~g['inside']] = 0
    # Geometry distances, observed variation and slopes are cheap routing inputs.
    distance = cdist(queries, normalized)
    nearest = np.argsort(distance, axis=1, kind='stable')[:, :min(3, len(o))]
    normalized_y = y/scales
    local_y = normalized_y[nearest]
    variation = np.ptp(local_y, axis=1)
    slopes = np.zeros_like(variation)
    curvature = np.zeros_like(variation)
    if len(o) >= 2:
        a, b = nearest[:, 0], nearest[:, 1]
        length = np.linalg.norm(normalized[a]-normalized[b], axis=1)
        slopes = (normalized_y[b]-normalized_y[a])/np.maximum(length[:, None], 1e-12)
    if len(o) >= 3:
        b, c = nearest[:, 1], nearest[:, 2]
        length = np.linalg.norm(normalized[b]-normalized[c], axis=1)
        next_slope = (normalized_y[c]-normalized_y[b])/np.maximum(length[:, None], 1e-12)
        curvature = next_slope-slopes
    coverage = np.column_stack([np.mean(support[:, j][None, :] < x[:, j, None], axis=1) for j in range(x.shape[1])])
    features = np.column_stack([g['features'], np.eye(len(SEGMENTS))[segment],
        np.full(len(x), rank), np.full(len(x), np.log1p(typical)),
        width_valid.astype(float), coverage, np.log1p(variation),
        np.sign(slopes)*np.log1p(np.abs(slopes)), np.sign(curvature)*np.log1p(np.abs(curvature))])
    if not np.isfinite(features).all(): raise ValueError('nonfinite routing features')
    return dict(segment=segment, features=features, geometry=g,
        width_prediction=width_prediction, width_valid=width_valid,
        typical_neighbor_distance=typical, feature_version='round3-support-v1')
