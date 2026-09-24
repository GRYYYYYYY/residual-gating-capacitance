"""Re-cut every cohort by interpolation regime: inside the table, or outside it.

The support partition of the frozen protocol already separates the two regimes
geometrically -- ``outside`` is the set of queries that lie outside the observed
convex hull or affine span, and the other four regions are inside it.  This
module collapses the five support regions into the two regimes the interpolation
question is actually about:

    regime 'inside'   表内插值  the table brackets the query
    regime 'outside'  表外外推  the query lies beyond the characterized range

Collapsing is a relabelling, not a re-pooling: a regime accumulator holds one
entry per (method, seed, process, family, protocol, ratio, mask seed) whose
segment field is the sentinel ``'all'``, so the verified recipe in
:mod:`unified.aggregate` applies to it unchanged and a regime score is computed
by exactly the same code path as every published number.  The sentinel means
"every query of this regime", and the true ``'all'`` segment (every query of the
cohort) is dropped, since keeping both would double count.
"""
import numpy as np

REGIMES = {'inside': ('missing_width', 'dense_1d', 'dense_nd', 'sparse_or_degenerate'),
           'outside': ('outside',)}
SENTINEL = 'all'


def regroup(accumulator, segment_of=None):
    """``{regime: accumulator}`` with each regime's support regions merged.

    ``segment_of`` optionally overrides the region membership, for slicing a
    regime further (for example by measured bracketing-cell width).
    """
    membership = segment_of or REGIMES
    out = {name: {} for name in membership}
    for key, cell in accumulator.items():
        segment = key[-1]
        for name, members in membership.items():
            if segment not in members:
                continue
            merged = (*key[:-1], SENTINEL)
            target = out[name].setdefault(merged, {'n': 0, 'se': np.zeros_like(cell['se']),
                                                   'sy': np.zeros_like(cell['sy'])})
            target['n'] += cell['n']
            target['se'] = target['se'] + cell['se']
            target['sy'] = target['sy'] + cell['sy']
    if any(not group for group in out.values()):
        missing = [name for name, group in out.items() if not group]
        raise ValueError(f'regime(s) with no records: {missing}; '
                         'was the accumulator built with per-region records?')
    return out


def coverage(accumulator, method, protocol, ratio=None):
    """Scored fraction of each (process, family) cell, for applicability reporting."""
    from .aggregate import resolve_ratio
    ratio = resolve_ratio(protocol, ratio)
    totals = {}
    for key, cell in accumulator.items():
        if key[0] != method or key[4] != protocol or key[5] != ratio:
            continue
        bucket = totals.setdefault((key[2], key[3]), [0, 0])
        bucket[0] += cell['n']
        bucket[1] += 1
    if not totals:
        raise ValueError('method not present for the requested condition')
    return totals
