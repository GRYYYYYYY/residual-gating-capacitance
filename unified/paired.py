"""Paired group bootstrap for the public cohort.

The manuscript's public intervals resample *associated groups* (tables sharing a
source file) and keep every mask of a group inside the same replicate.  This
module reproduces that convention for any pair of methods, using the same
mask-macro recipe as :mod:`unified.aggregate`: per mask, pool squared error and
truth energy inside (process, family, target) cells, macro-average the defined
NRMSEs, then average over masks.  The recomputed statistic is the *difference*
of the two methods' scores, so the interval is paired.
"""
import gzip
import json
from pathlib import Path

import numpy as np

from .aggregate import WIDTH_PROTOCOL, resolve_ratio


def _read(path):
    path = Path(path)
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def group_accumulator(paths, methods, segments=('all',), limit=None):
    """Sparse sums keyed by (method, protocol, ratio, mask, group, cell) -> vector.

    ``segments`` selects which support regions enter the statistic.  A record
    file holds one row per (episode, method, region), and the regions partition
    the queries while the 'all' row covers them collectively; pooling both would
    count every query twice.  Doubling is harmless for a ratio-of-sums score but
    is still wrong, so the selection is explicit and defaults to 'all'.
    """
    methods = list(methods)
    if len(set(methods)) != len(methods):
        raise ValueError('duplicate method in the paired comparison')
    segments = (segments,) if isinstance(segments, str) else tuple(segments)
    cells, groups_seen, groups = {}, {}, []
    for path in paths:
        for row in _read(path):
            method = row['method']
            if method not in methods or row.get('segment', 'all') not in segments:
                continue
            group = row.get('dependency_group') or row['split_group']
            if group not in groups_seen:
                groups_seen[group] = len(groups)
                groups.append(group)
            key = (method, row['protocol'], row['ratio'], int(row['mask_seed']), group,
                   (row['process_id'], row['family']))
            entry = cells.get(key)
            if entry is None:
                entry = cells[key] = [np.zeros(len(row['squared_error']), float),
                                      np.zeros(len(row['squared_error']), float)]
            entry[0] += np.asarray(row['squared_error'], float)
            entry[1] += np.asarray(row['squared_truth'], float)
    if not cells:
        raise ValueError('no records matched the requested methods')
    return dict(cells=cells, groups=groups, group_index=groups_seen, methods=methods,
                shape=_shape(cells))


def _shape(cells):
    protocols, ratios, masks, cells_seen = [], [], [], {}
    targets = 0
    for (_, protocol, ratio, mask, _, cell), entry in cells.items():
        for bucket, value in ((protocols, protocol), (ratios, ratio), (masks, mask)):
            if value not in bucket:
                bucket.append(value)
        cells_seen.setdefault(cell, len(cells_seen))
        targets = max(targets, len(entry[0]))
    return dict(protocols=protocols, ratios=sorted(ratios, key=lambda value: (value is None, value)),
                masks=sorted(masks), cells=list(cells_seen), cell_index=cells_seen, targets=targets)


def dense(accumulator, method, protocol, ratio, mask):
    """[n_groups, n_cells, n_targets] error and truth arrays for one condition."""
    shape = accumulator['shape']
    if protocol not in shape['protocols']:
        raise ValueError(f'protocol {protocol} absent')
    se = np.zeros((len(accumulator['groups']), len(shape['cells']), shape['targets']))
    sy = np.zeros_like(se)
    for (name, item_protocol, item_ratio, item_mask, group, cell), entry in accumulator['cells'].items():
        if name != method or item_protocol != protocol or item_ratio != ratio or item_mask != mask:
            continue
        row, column = accumulator['group_index'][group], shape['cell_index'][cell]
        se[row, column] += entry[0]
        sy[row, column] += entry[1]
    return se, sy


def prepare(accumulator, protocol, ratio):
    """Pre-gather the dense arrays needed for every mask of one condition."""
    shape = accumulator['shape']
    ratio = resolve_ratio(protocol, ratio)
    if protocol not in shape['protocols']:
        raise ValueError(f'protocol {protocol} not present in the accumulator')
    stacked = {method: [dense(accumulator, method, protocol, ratio, mask) for mask in shape['masks']]
               for method in accumulator['methods']}
    return dict(protocol=protocol, ratio=ratio, masks=list(shape['masks']), stacked=stacked,
                shape=shape, group_index=accumulator['group_index'])


def _mask_macro(se, sy, draw):
    pooled_error = se[draw].sum(axis=0)
    pooled_truth = sy[draw].sum(axis=0)
    defined = pooled_truth > 0
    if not defined.any():
        return None
    return float(np.sqrt(pooled_error[defined] / pooled_truth[defined]).mean())


def _score(prepared, method, draw):
    values = []
    for se, sy in prepared['stacked'][method]:
        value = _mask_macro(se, sy, draw)
        if value is not None:
            values.append(value)
    if not values:
        return None
    return float(np.mean(values))


def bootstrap_delta(prepared, method, reference, replicates=2000, seed=20260922):
    order = np.arange(len(prepared['group_index']))
    observed = _score(prepared, method, order)
    baseline = _score(prepared, reference, order)
    if observed is None or baseline is None:
        raise ValueError('undefined score for the requested pair')
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(replicates):
        draw = rng.integers(0, len(order), len(order))
        left = _score(prepared, method, draw)
        right = _score(prepared, reference, draw)
        if left is None or right is None:
            continue
        deltas.append(left - right)
    if len(deltas) < replicates // 2:
        raise ValueError('too many undefined bootstrap replicates')
    deltas = np.asarray(deltas, float)
    return dict(method=method, reference=reference, protocol=prepared['protocol'],
                ratio=prepared['ratio'], method_score=observed, reference_score=baseline,
                delta=observed - baseline, replicates=len(deltas),
                group_count=len(order),
                low=float(np.quantile(deltas, .025)), high=float(np.quantile(deltas, .975)),
                probability_better=float((deltas < 0).mean()))
