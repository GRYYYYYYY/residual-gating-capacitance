"""Commercial multilinear interpolation and the sibling table interpolators.

`docs/baseline.md` defines the comparison set as the interpolation *step* of a
parasitic-extraction table:

    CMI-1D      piecewise linear, 2 bracketing samples
    CMI-2D      bilinear, 4 bracketing corners
    CMI-4D      quadrilinear, 16 vertices of the bracketing 4-D cell
    OpenRCX-LI  separation-axis piecewise linear at the query's neighbouring widths
    PCHIP / IDW / GP   general numerical and statistical baselines

CMI-1D, CMI-2D and CMI-4D are one operator -- multilinear interpolation on the
2^d vertices of the bracketing cell of a d-dimensional grid -- so they are
implemented once, at d = 1, 2, 4.  A d-dimensional rule is only defined on a
table of rank d; a rank mismatch is reported as inapplicability.

A sparse characterization removes nodes, so the cell that encloses a query may
not be complete.  Three rules make the comparison well defined, and all three
reduce to the textbook operator on a complete grid (verified to $10^{-16}$ on
affine fields at ranks 1, 2 and 4):

1. an unobserved node is bracketed by the nearest *observed* nodes strictly on
   either side, so the cell widens by a grid step rather than collapsing onto
   the missing node;
2. a corner of the widened cell that is still unobserved is completed by the
   nearest observed node in index space, with deterministic tie-breaking;
3. a query outside the observed range clamps to the boundary node, the
   no-extrapolation convention of the frozen classical controls.

Each method reports the width of the cell it had to use, because that widening
is exactly what the table no longer constrains.  Every method that cannot answer
falls back to one common floor, so all methods are scored on the same population
and none benefits from abstaining.
"""
import numpy as np

from .workspace import archive_on_path

archive_on_path()

from pdkcap.interpolation import predict, reduce_coordinates  # noqa: E402

METHODS = ('cmi1d', 'cmi2d', 'cmi4d', 'openrcx_li', 'pchip', 'idw', 'gp')
#: Original coordinate index carrying separation / coupling distance.
SEPARATION_COORDINATE = 1


def node_tables(reduced, dims):
    """Observed node values per axis and node index tuple -> support row."""
    values = [np.unique(reduced[:, axis]) for axis in range(dims)]
    lookup = {}
    digits = [np.searchsorted(values[axis], reduced[:, axis]) for axis in range(dims)]
    for row in range(len(reduced)):
        key = tuple(int(digit[row]) for digit in digits)
        if key in lookup:
            raise ValueError('duplicate grid node in the support')
        lookup[key] = row
    return values, lookup


def nearest_key(key, available, keys_array):
    """Observed grid node nearest to ``key`` in index space, deterministically.

    Ties are broken by the lexicographically smaller index tuple, so the
    completion never depends on set iteration order.
    """
    distance = np.abs(keys_array - np.asarray(key, int)).sum(axis=1)
    best = int(np.argmin(distance))
    tied = np.flatnonzero(distance == distance[best])
    if len(tied) > 1:
        best = int(tied[np.lexsort(keys_array[tied].T[::-1])[0]])
    return available[best]


def bracket(nodes, point):
    """Largest node index at or below ``point`` and smallest at or above it."""
    position = int(np.searchsorted(nodes, point))
    if position < len(nodes) and nodes[position] == point:
        return position, position
    low = min(max(position - 1, 0), len(nodes) - 1)
    high = min(max(position, 0), len(nodes) - 1)
    return low, high


def axis_lines(lookup, dims):
    """Observed nodes grouped by the coordinates they do *not* vary in.

    ``lines[axis][rest]`` lists ``(index_along_axis, support_row)`` sorted by
    index for every observed node whose other coordinates are ``rest``.  It is
    what makes the missing-corner completion a lookup instead of a search.
    """
    lines = [{} for _ in range(dims)]
    for key, row in lookup.items():
        for axis in range(dims):
            rest = key[:axis] + key[axis + 1:]
            lines[axis].setdefault(rest, []).append((key[axis], row))
    for axis in range(dims):
        for rest in lines[axis]:
            lines[axis][rest].sort()
    return lines


def line_completion(key, lines, dims):
    """Interpolate an unobserved corner along the axis that brackets it best.

    A missing entry of a rule table is estimated the way a table-completion
    pass estimates it: pick an axis on which this entry has observed
    neighbours strictly either side with the other coordinates held fixed, and
    interpolate between them.  The axis with the tightest bracketing pair wins.
    Returns ``{support_row: weight}`` or ``None`` when no axis brackets.
    """
    best = None
    for axis in range(dims):
        line = lines[axis].get(key[:axis] + key[axis + 1:])
        if not line or len(line) < 2:
            continue
        indices = [item[0] for item in line]
        position = int(np.searchsorted(indices, key[axis]))
        if position == 0 or position == len(line):
            continue
        low, high = line[position - 1], line[position]
        if low[0] == high[0]:
            continue
        share = (key[axis] - low[0]) / (high[0] - low[0])
        margin = max(key[axis] - low[0], high[0] - key[axis])
        if best is None or margin < best[0]:
            best = (margin, {low[1]: 1. - share, high[1]: share})
    return None if best is None else best[1]


def multilinear(reduced, values, query, dims, floor):
    """Multilinear interpolation on the bracketing observed cell of a rank-``dims`` grid.

    Returns ``(prediction, cell_width, adjacent)``: predictions over every query
    row, the width of the cell each query had to use (in units of the axis
    range), and a flag for queries whose cell is a single grid step in every
    axis -- the regime in which the commercial rule is exactly defined.
    """
    if dims < 1:
        raise ValueError('positive interpolation order required')
    prediction = np.array(floor, float)
    width = np.full(len(query), np.nan)
    adjacent = np.zeros(len(query), bool)
    if reduced.shape[1] != dims:
        return prediction, width, adjacent
    nodes, lookup = node_tables(reduced, dims)
    available = list(lookup)
    keys_array = np.asarray(available, int)
    lines = axis_lines(lookup, dims)
    present = [np.asarray(sorted({key[axis] for key in lookup}), int) for axis in range(dims)]
    ranges = np.array([nodes[axis][-1] - nodes[axis][0] for axis in range(dims)], float)
    ranges[ranges <= 0] = 1.
    for row, point in enumerate(query):
        position = [int(np.searchsorted(nodes[axis], point[axis])) for axis in range(dims)]
        exact = all(position[axis] < len(nodes[axis])
                    and nodes[axis][position[axis]] == point[axis] for axis in range(dims))
        low, high, span = [], [], np.zeros(dims)
        if exact and tuple(position) in lookup:
            low, high = list(position), list(position)
        else:
            # The query is not a characterized node: bracket it between the
            # nearest observed nodes strictly on either side, so an unobserved
            # node widens the cell instead of collapsing onto itself.
            for axis in range(dims):
                index = present[axis]
                below = index[index < position[axis]]
                above = (index[index > position[axis]] if exact
                         else index[index >= position[axis]])
                low.append(int(below[-1]) if len(below) else int(above[0]))
                high.append(int(above[0]) if len(above) else int(below[-1]))
        for axis in range(dims):
            span[axis] = nodes[axis][high[axis]] - nodes[axis][low[axis]]
        weight = {}
        for mask in range(1 << dims):
            key = tuple(high[axis] if (mask >> axis) & 1 else low[axis] for axis in range(dims))
            value = 1.0
            for axis in range(dims):
                lo, hi = low[axis], high[axis]
                if lo == hi:
                    continue
                share = (point[axis] - nodes[axis][lo]) / (nodes[axis][hi] - nodes[axis][lo])
                value *= share if (mask >> axis) & 1 else (1.0 - share)
            weight[key] = weight.get(key, 0.) + value
        # Every axis takes its bracketing values from that axis's observed
        # nodes, so a corner of the bracketing cell can still be unobserved.  It
        # is estimated by one-dimensional interpolation along whichever axis
        # brackets it, and only when no axis brackets it does the completion
        # fall back to the nearest observed node in index space.  On a complete
        # grid every corner is observed and the rule is exactly multilinear.
        usable = {}
        for key in weight:
            if key in lookup:
                usable[key] = {lookup[key]: 1.0}
            else:
                terms = line_completion(key, lines, dims)
                usable[key] = (terms if terms is not None
                               else {lookup[nearest_key(key, available, keys_array)]: 1.0})
        total = sum(weight[key] for key in usable)
        if not usable or total <= 0:
            continue
        prediction[row] = sum(
            weight[key] * sum(share * values[index] for index, share in terms.items())
            for key, terms in usable.items()) / total
        width[row] = float((span / ranges).max())
        adjacent[row] = bool(np.all(span <= _smallest_gap(nodes, dims)))
    return prediction, width, adjacent


def _smallest_gap(nodes, dims):
    gaps = []
    for axis in range(dims):
        difference = np.diff(nodes[axis])
        gaps.append(difference.min() if len(difference) else 0.)
    return np.asarray(gaps, float) * (1. + 1e-9)


def separation_curve(reduced, values, query, dims, floor, curve_axis, reference_axis, kind):
    """Piecewise linear or PCHIP along ``curve_axis`` between neighbouring ``reference_axis`` rows.

    This is the OpenRCX rule generalised to a sparse table: the query's width is
    bracketed between observed widths, separation interpolation is done inside
    each bracketing row, and the two results are blended linearly in width.
    """
    from scipy.interpolate import PchipInterpolator
    prediction = np.array(floor, float)
    width = np.full(len(query), np.nan)
    adjacent = np.zeros(len(query), bool)
    if dims < 2 or reference_axis == curve_axis:
        return prediction, width, adjacent
    reference = np.unique(reduced[:, reference_axis])
    reference_range = reference[-1] - reference[0] or 1.
    reference_gap = float(np.diff(reference).min()) if len(reference) > 1 else 0.
    curve_range = reduced[:, curve_axis].ptp() or 1.
    for row, point in enumerate(query):
        lo, hi = bracket(reference, point[reference_axis])
        levels = [reference[lo]] if lo == hi else [reference[lo], reference[hi]]
        estimates = []
        for level in levels:
            rows = np.flatnonzero(reduced[:, reference_axis] == level)
            if len(rows) < 1:
                continue
            order = rows[np.argsort(reduced[rows, curve_axis])]
            grid = reduced[order, curve_axis]
            clipped = float(np.clip(point[curve_axis], grid[0], grid[-1]))
            if kind == 'pchip' and len(grid) > 1 and len(np.unique(grid)) == len(grid):
                estimates.append(PchipInterpolator(grid, values[order], axis=0)(clipped))
            elif len(grid) > 1:
                estimates.append(np.column_stack([np.interp(clipped, grid, values[order, j])
                                                  for j in range(values.shape[1])]))
            else:
                estimates.append(values[order[0]])
        if not estimates:
            continue
        if len(estimates) == 1:
            prediction[row] = estimates[0]
        else:
            share = (point[reference_axis] - reference[lo]) / (reference[hi] - reference[lo])
            prediction[row] = (1. - share) * estimates[0] + share * estimates[1]
        width[row] = max((reference[hi] - reference[lo]) / reference_range, 0.)
        adjacent[row] = bool((reference[hi] - reference[lo]) <= reference_gap * (1. + 1e-9))
    return prediction, width, adjacent


def interpolation_set(table, observed, values, query):
    """Every classical method of `docs/baseline.md` on one observed support.

    Returns ``(methods, floor, floor_policy)``; ``methods`` maps a name to
    ``(prediction, cell_width, adjacent, policy)`` over all candidate geometries.
    """
    x = np.asarray(table['coordinates'], float)
    observed = np.asarray(observed, int)
    values = np.asarray(values, float)
    floor, policy = predict(x[observed], values, x, 'linear')
    reduced, queries, axes = reduce_coordinates(x[observed], x)
    dims = len(axes)
    separation = axes.index(SEPARATION_COORDINATE) if SEPARATION_COORDINATE in axes else 0
    other = next((axis for axis in range(dims) if axis != separation), separation)
    out = {}

    def finish(prediction, width, adjacent, note):
        prediction = np.maximum(prediction, 0.)
        prediction[observed] = values
        width = np.where(np.isfinite(width), width, 1.)
        return prediction, width, adjacent, note

    for name, order in (('cmi1d', 1), ('cmi2d', 2), ('cmi4d', 4)):
        if order != dims:
            out[name] = finish(floor.copy(), np.ones(len(x)), np.zeros(len(x), bool),
                               f'inapplicable: table rank {dims} != {order}')
            continue
        prediction, width, adjacent = multilinear(reduced, values, queries, order, floor)
        out[name] = finish(prediction, width, adjacent,
                           f'{order}-D multilinear on bracketing observed nodes')
    # A one-dimensional table *is* a separation table, so OpenRCX-LI and PCHIP
    # reduce to their one-dimensional rules there rather than becoming undefined.
    for name, kind in (('openrcx_li', 'linear'), ('pchip', 'pchip')):
        if dims < 2:
            if kind == 'pchip':
                prediction, info = predict(x[observed], values, x, 'pchip')
                out[name] = finish(prediction, np.ones(len(x)), np.ones(len(x), bool), info['policy'])
            else:
                prediction, width, adjacent = multilinear(reduced, values, queries, 1, floor)
                out[name] = finish(prediction, width, adjacent, '1-D separation piecewise linear')
            continue
        prediction, width, adjacent = separation_curve(reduced, values, queries, dims, floor,
                                                       separation, other, kind)
        out[name] = finish(prediction, width, adjacent,
                           f'{kind} along coordinate {axes[separation]} between neighbouring '
                           f'coordinate {axes[other]} rows')
    for name in ('idw', 'gp'):
        prediction, info = predict(x[observed], values, x, name)
        out[name] = finish(prediction, np.zeros(len(x)), np.ones(len(x), bool), info['policy'])
    return out, floor, policy
