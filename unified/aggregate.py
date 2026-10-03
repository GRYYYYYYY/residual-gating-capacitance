"""Reproduce the paper's mean-mask macro NRMSE aggregation.

This module aggregates the released per-record errors using the exact recipe
below. Result-table source mappings are provided in docs/FINAL_PAPER.md.

-----------------------------------------------------------------------------
The verified recipe (this is the whole definition; nothing else is applied)
-----------------------------------------------------------------------------
Notation: a *record* is one scored (method, seed, protocol, ratio, mask seed,
process, family, segment) cell of one table group.  It carries ``n`` and two
per-target vectors: ``squared_error`` (sum of squared pointwise errors) and
``squared_truth`` (sum of squared truth values, i.e. the normalising energy).

1. POOL, do not average, everything that shares a *cell key*

       (method, training_seed, process_id, family, protocol, ratio,
        mask_seed, segment)

   by summing ``n``, ``squared_error`` and ``squared_truth`` over records.
   A (process, family, target) triple is therefore a *component group*: its
   raw scores are the pooled sums, never a mean of per-table ratios.

2. PER-TARGET NRMSE inside that group, for every target ``j``:

       nrmse_j = sqrt( sum_a squared_error_j / sum_a squared_truth_j )

   and it is DEFINED ONLY WHEN ``sum_a squared_truth_j > 0``.  Zero-truth
   components are dropped (``sy > 0``, strict); they are never counted as
   zero error and never counted as zero in any denominator.

3. MACRO OVER COMPONENT GROUPS WITHIN A MASK.  The per-mask macro is the
   arithmetic mean of the flat list of *all* defined ``nrmse_j`` over every
   (process, family, target) group of that (method, seed, protocol, ratio,
   segment, mask_seed).  Flat is important in general: a target that is
   undefined in one (process, family) group contributes no entry, so this is
   *not* "mean over families of the mean over targets" unless the defined
   targets line up.  In the frozen cohorts they do line up -- every public cell
   carries exactly 2 targets and every reference/transfer cell exactly 3, so
   within a cohort the nesting order over process/family/target is immaterial
   here; the flat form is the producer's and is implemented as such, so a new
   model whose cells mix target counts is still aggregated correctly.

4. MEAN OVER MASKS.  The reported score is the arithmetic mean of the per-mask
   macros over mask seeds.  A mask seed with no defined component contributes
   nothing (it is not a zero and not a NaN); ``mask_count`` is the number of
   mask seeds that did contribute.  This is why the same (method, protocol)
   can have ``mask_count`` 5 (seeds 11/29/47/71/101) or 8 (seeds 0..7).

5. PROTOCOL / RATIO SELECTION.  ``mcar`` (display name *Random*), ``block`` and
   ``extrapolation`` are read at ``ratio == 0.3``.  ``width`` (whole-width
   holdout) is stored with ``ratio == None`` (JSON ``null``); ``None`` is a real
   key, not "unfiltered".

   The record's ``protocol`` string is literally ``"mcar"`` -- *Random* is only
   the manuscript's display name, so no key alias is needed.

   ``training_seed`` is likewise part of the condition (:data:`SEED_BY_METHOD`
   holds the seed the manuscript uses per baseline: ``classical`` for the
   classical interpolants, ``ensemble`` for the learned baselines,
   ``deterministic`` for the frozen deployment).  Seeds 0/1/2 that the same
   method also carries are *different* populations and are never pooled in.

Ordering notes that do not change the answer: sums are accumulated in file
order and means are computed with ``numpy.mean`` on Python lists, exactly as
the frozen producer did; the only remaining freedom is summation order, whose
effect on a mask mean is ~1e-16 relative, far inside the 1e-9 self-test
tolerance.  The self-test nevertheless checks equality to 1e-9 against every
published cell, not to a rounded print precision.

Sanity anchor for a human reader: variants that look equivalent are not, and the
self-test pins the real one.  For Linear mcar@0.3 the frozen summary's own
``macro`` rows give 0.2362 (published) while the mask-pooled macro
(one sqrt(sum_se/sum_sy) after summing all five mask seeds) gives 0.2660, and
pooling ratios as well as masks gives 0.2913 -- and at ratio 0.5 the ordering
flips (0.3158 mask-separated vs 0.2972 mask-pooled), so no single pooled
estimator stands in for the published one.  Keeping masks separate and pooling
squared errors before the ratio, as above, is what reproduces the table.

Public API
----------
    stream_records(path, acc=None, progress=None, stats=None) -> accumulator
    add_records(acc, path, progress=None, stats=None)         -> acc (in place)
    merge_accumulators(*accs)                                 -> new accumulator
    baseline_with(new_records, cache=...)                     -> baseline + new model
    mask_scores(acc, method, protocol, ratio=AUTO, segment='all',
                training_seed=AUTO, index=None)               -> {mask_seed: macro}
    mask_macro_nrmse(acc, method, protocol, ratio=AUTO, segment='all',
                     training_seed=AUTO, index=None)          -> float | None
    cell_rows(acc, method, protocol, ...)                     -> list[dict] (audit)
    condition_index(acc) / condition(acc, ...)                -> selection helpers
    save_accumulator / load_accumulator / accumulator_payload / accumulator_from_payload

Run ``python -m unified.aggregate`` for final-paper record verification.
The aggregation functions below are unchanged; obsolete result snapshots are removed.
"""
import argparse
import gzip
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

try:  # package import (python -m unified.aggregate)
    from .workspace import ARCHIVE, ROOT, file_hash
except ImportError:  # direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from unified.workspace import ARCHIVE, ROOT, file_hash

# ---------------------------------------------------------------------------
# Constants.  Changing any of these changes the published numbers.
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent

#: Frozen cohorts, i.e. the run directories holding ``records.jsonl.gz``.
COHORTS = {
    'public': ARCHIVE / 'runs/bl3_public_conf',
    'reference': ARCHIVE / 'runs/bl3_reference_conf',
    'to_asap7': ARCHIVE / 'runs/bl3_to_asap7_conf',
}
RECORDS_NAME = 'records.jsonl.gz'

#: Accumulator key layout.  ``target`` is deliberately *not* a key component:
#: it is the index into the per-target ``se`` / ``sy`` vectors (step 2 above),
#: exactly as in the frozen producer, which accumulated ``np.asarray`` vectors.
#: A caller who wants per-target keys can call :func:`cell_rows`.
KEY_FIELDS = ('method', 'training_seed', 'process_id', 'family', 'protocol',
              'ratio', 'mask_seed', 'segment')

#: Human summary of the macro nesting, innermost first.
MACRO_ORDER = (
    'pool squared_error/squared_truth/n over records of one cell key',
    'per-target sqrt(sum_se/sum_sy), defined only when sum_sy > 0',
    'macro = mean over the flat list of (process, family, target) cells, per mask_seed',
    'score = mean of the per-mask macros over mask_seed (empty masks dropped)',
)

SEGMENTS = ('all', 'outside', 'missing_width', 'dense_1d', 'dense_nd', 'sparse_or_degenerate')
DEFAULT_SEGMENT = 'all'

#: ``training_seed`` is part of the aggregation condition, not a nuisance
#: parameter: seeds 0/1/2 of the same method are *separate* populations, and
#: pooling them silently changes every published number.  These are the seeds
#: the manuscript's table builder passes for the frozen baselines
#: (``paper/round3_date_v2/build_assets.py``, ``manuscript_methods``).
SEED_BY_METHOD = {
    'linear': 'classical', 'pchip': 'classical', 'gp': 'classical', 'idw': 'classical',
    'width_linear': 'classical',
    'width_pchip': 'classical', 'width_gp': 'classical',
    'original_dro': 'ensemble', 'original_residual': 'ensemble', 'original_direct': 'ensemble',
    'retrained_dro': 'ensemble', 'retrained_residual': 'ensemble',
    'hard_local': 'ensemble', 'hard_boundary': 'ensemble', 'hard_both': 'ensemble',
    'gated_none': 'ensemble', 'gated_both': 'ensemble',
    'shrink_0.75': 'ensemble', 'risk': 'ensemble', 'top2': 'ensemble',
    'fixed': 'deterministic', 'round3_selected': 'selected',
}

#: Protocol strings as stored in records; the manuscript display names.
PROTOCOL_DISPLAY = {'mcar': 'Random', 'block': 'Block', 'extrapolation': 'Extrap.', 'width': 'Width'}
WIDTH_PROTOCOL = 'width'
DEFAULT_RATIO = 0.3

#: Sentinel for "use the manuscript's ratio convention for this protocol".
AUTO = 'auto'

REQUIRED_FIELDS = ('method', 'training_seed', 'process_id', 'family', 'protocol',
                   'ratio', 'mask_seed', 'segment', 'n',
                   'squared_error', 'squared_truth')

ACC_FORMAT = 'pdkcap-mask-accum-v1'


#: Baseline cache location (a NEW directory; never overwritten).
CACHE_DIR = ROOT / 'runs/baseline_accum_v1'
CACHE_NAME = 'public.json'
RECEIPT_NAME = 'receipt.json'


# ---------------------------------------------------------------------------
# Streaming accumulation
# ---------------------------------------------------------------------------

def resolve_ratio(protocol, ratio=AUTO):
    """The manuscript's ratio convention: width has no ratio, others use 0.3.

    :data:`AUTO` means "what the manuscript does".  An explicit ``None`` selects
    the null-ratio cells, which are real keys for ``width`` and simply do not
    exist for the missingness protocols; an explicit number selects that ratio.
    """
    if ratio is not AUTO and ratio is not None:
        return ratio
    if ratio is None and protocol != WIDTH_PROTOCOL:
        return None
    return None if protocol == WIDTH_PROTOCOL else DEFAULT_RATIO


def records_path(run_or_file):
    """Accept either a run directory or a records file path."""
    path = Path(run_or_file)
    if path.is_dir():
        path = path / RECORDS_NAME
    if not path.exists():
        raise FileNotFoundError(f'records file not found: {path}')
    if path.suffixes[-2:] != ['.jsonl', '.gz']:
        raise ValueError(f'expected a *.jsonl.gz record file, got {path}')
    return path


def _vector(row, field, source, line):
    value = row[field]
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f'{source}:{line}: {field!r} must be a non-empty list, got {value!r}')
    out = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f'{source}:{line}: {field!r} has a non-numeric entry {item!r}')
        item = float(item)
        if not math.isfinite(item) or item < 0.0:
            raise ValueError(f'{source}:{line}: {field!r} has a non-finite/negative entry {item!r}')
        out.append(item)
    return out


def _record(row, source, line):
    """Validate one record and return (key, n, se, sy).  Never skips silently."""
    for field in REQUIRED_FIELDS:
        if field not in row:
            raise ValueError(f'{source}:{line}: record is missing required field {field!r}')
    segment = row['segment']
    if segment not in SEGMENTS:
        raise ValueError(f'{source}:{line}: unknown segment {segment!r}; known: {SEGMENTS}')
    ratio = row['ratio']
    if ratio is not None:
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(ratio):
            raise ValueError(f'{source}:{line}: ratio must be a finite number or null, got {ratio!r}')
    protocol = row['protocol']
    if not isinstance(protocol, str) or not protocol:
        raise ValueError(f'{source}:{line}: protocol must be a non-empty string')
    n = row['n']
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError(f'{source}:{line}: n must be a non-negative integer, got {n!r}')
    se = _vector(row, 'squared_error', source, line)
    sy = _vector(row, 'squared_truth', source, line)
    if len(se) != len(sy):
        raise ValueError(f'{source}:{line}: squared_error/squared_truth length mismatch '
                         f'({len(se)} vs {len(sy)})')
    for field in ('method', 'training_seed', 'process_id', 'family'):
        if not isinstance(row[field], str) or not row[field]:
            raise ValueError(f'{source}:{line}: {field!r} must be a non-empty string')
    mask_seed = row['mask_seed']
    if isinstance(mask_seed, bool) or not isinstance(mask_seed, int):
        raise ValueError(f'{source}:{line}: mask_seed must be an integer, got {mask_seed!r}')
    key = (row['method'], row['training_seed'], row['process_id'], row['family'],
           protocol, ratio, mask_seed, segment)
    return key, n, se, sy


def stream_records(path, acc=None, progress=None, stats=None):
    """Stream a ``records.jsonl.gz`` into a fresh/merged accumulator.

    Returns ``{key: {'n': int, 'se': [float, ...], 'sy': [float, ...]}}`` with
    ``key`` a :data:`KEY_FIELDS` tuple and ``se``/``sy`` indexed by target.
    ``progress`` is an optional callable invoked every 500k records; ``stats``
    is an optional dict that receives ``records``, ``bytes`` and ``path`` for
    run receipts.
    """
    path = records_path(path)
    acc = {} if acc is None else acc
    lengths = {key: len(value['se']) for key, value in acc.items()}
    source = str(path)
    count = 0
    with gzip.open(path, 'rt') as handle:
        for line, text in enumerate(handle, 1):
            text = text.strip()
            if not text:
                continue
            count += 1
            row = json.loads(text)
            if not isinstance(row, dict):
                raise ValueError(f'{source}:{line}: record is not a JSON object')
            key, n, se, sy = _record(row, source, line)
            cell = acc.get(key)
            if cell is None:
                acc[key] = {'n': n, 'se': list(se), 'sy': list(sy)}
                lengths[key] = len(se)
            else:
                width = lengths[key]
                if len(se) != width:
                    raise ValueError(f'{source}:{line}: target count {len(se)} conflicts with '
                                     f'{width} already accumulated for {key}')
                cell['n'] += n
                cell_se, cell_sy = cell['se'], cell['sy']
                for j in range(width):  # same order as the frozen producer
                    cell_se[j] += se[j]
                    cell_sy[j] += sy[j]
            if progress is not None and count % 500000 == 0:
                progress(count)
    if stats is not None:
        stats.update(records=count, path=source, bytes=path.stat().st_size,
                     cell_keys=len(acc))
    return acc


def add_records(acc, path, progress=None, stats=None):
    """Merge another records file into ``acc`` in place and return ``acc``.

    Used to pool a new model's records with the frozen baseline's records
    before scoring them with :func:`mask_macro_nrmse`.  Keys that already exist
    keep their position; new keys are appended.
    """
    if not isinstance(acc, dict):
        raise TypeError('acc must be the dict returned by stream_records')
    return stream_records(path, acc=acc, progress=progress, stats=stats)


def merge_accumulators(*accs):
    """Return a new accumulator holding the union (sums) of the inputs."""
    merged = {}
    for acc in accs:
        if not isinstance(acc, dict):
            raise TypeError('merge_accumulators takes accumulator dicts')
        for key, value in acc.items():
            if tuple(key) != tuple(KEY_FIELDS) and len(key) != len(KEY_FIELDS):
                raise ValueError(f'accumulator key has {len(key)} fields, expected {len(KEY_FIELDS)}')
            cell = merged.get(key)
            if cell is None:
                merged[key] = {'n': value['n'], 'se': list(value['se']), 'sy': list(value['sy'])}
                continue
            if len(cell['se']) != len(value['se']):
                raise ValueError(f'target count mismatch while merging {key}')
            cell['n'] += value['n']
            for j in range(len(cell['se'])):
                cell['se'][j] += value['se'][j]
                cell['sy'][j] += value['sy'][j]
    return merged


# ---------------------------------------------------------------------------
# The aggregation itself
# ---------------------------------------------------------------------------

def seeds_for(acc, method):
    """Training seeds present for ``method``, in first-appearance order."""
    seen = []
    for key in acc:
        if key[0] == method and key[1] not in seen:
            seen.append(key[1])
    return seen


def resolve_seed(acc, method, training_seed=AUTO):
    """Resolve the ``training_seed`` component of the condition.

    Explicit strings pass through.  :data:`AUTO` uses :data:`SEED_BY_METHOD`
    (the manuscript's own choice per baseline); for a method that is not in that
    table it uses the method's only seed when there is exactly one, and
    otherwise raises rather than silently pooling seeds.
    """
    if training_seed is not AUTO:
        if not isinstance(training_seed, str) or not training_seed:
            raise ValueError(f'training_seed must be a non-empty string, got {training_seed!r}')
        return training_seed
    if method in SEED_BY_METHOD:
        return SEED_BY_METHOD[method]
    present = seeds_for(acc, method)
    if len(present) == 1:
        return present[0]
    if not present:
        return SEED_BY_METHOD.get(method, 'ensemble')
    raise ValueError(f'method {method!r} has several training seeds {present}; '
                     'pass training_seed explicitly (pooling them is not the manuscript definition)')


def condition_index(acc):
    """``{(method, seed, protocol, ratio, segment): {mask_seed: [cell_key, ...]}}``.

    Holds references to the existing keys only (no numeric copies), so it is
    cheap even for the 3M-record public cohort, and it is rebuilt per call so
    it can never go stale.  :func:`mask_scores` accepts one to avoid rescanning
    the accumulator for every table cell.
    """
    if not isinstance(acc, dict):
        raise TypeError('acc must be an accumulator dict')
    index = {}
    for key in acc:
        if len(key) != len(KEY_FIELDS):
            raise ValueError(f'accumulator key has {len(key)} fields, expected {len(KEY_FIELDS)}')
        index.setdefault((key[0], key[1], key[4], key[5], key[7]), {}).setdefault(key[6], []).append(key)
    return index


def condition(acc, method, protocol, ratio=AUTO, segment=DEFAULT_SEGMENT, training_seed=AUTO):
    """The five-tuple ``(method, seed, protocol, ratio, segment)`` actually used."""
    if segment not in SEGMENTS:
        raise ValueError(f'unknown segment {segment!r}; known: {SEGMENTS}')
    return (method, resolve_seed(acc, method, training_seed), protocol,
            resolve_ratio(protocol, ratio), segment)


def _select(acc, condition_key, index=None):
    """Return the cell keys of one condition, in accumulator order."""
    if index is not None:
        return [key for keys in index.get(condition_key, {}).values() for key in keys]
    return [key for key in acc
            if (key[0], key[1], key[4], key[5], key[7]) == condition_key]


def cell_rows(acc, method, protocol, ratio=AUTO, segment=DEFAULT_SEGMENT,
              training_seed=AUTO, index=None):
    """Audit rows: one dict per (mask_seed, process, family, target) group."""
    if not isinstance(acc, dict):
        raise TypeError('acc must be an accumulator dict')
    rows = []
    for key in _select(acc, condition(acc, method, protocol, ratio, segment, training_seed), index):
        cell = acc[key]
        for target in range(len(cell['se'])):
            se, sy = cell['se'][target], cell['sy'][target]
            rows.append({'mask_seed': key[6], 'process_id': key[2], 'family': key[3],
                         'target': target, 'n': cell['n'], 'squared_error': se,
                         'squared_truth': sy,
                         'nrmse': float(np.sqrt(np.float64(se) / np.float64(sy))) if sy > 0 else None})
    return rows


def mask_scores(acc, method, protocol, ratio=AUTO, segment=DEFAULT_SEGMENT,
                training_seed=AUTO, index=None):
    """Per-mask macro NRMSE, ``{mask_seed: value}`` in first-appearance order.

    One entry per contributing mask seed; a mask seed with no defined component
    group is absent (it is not a zero).  Returns ``{}`` when the condition has
    no records at all.
    """
    if not isinstance(acc, dict):
        raise TypeError('acc must be an accumulator dict')
    by_mask = {}
    for key in _select(acc, condition(acc, method, protocol, ratio, segment, training_seed), index):
        cell = acc[key]
        values = by_mask.setdefault(key[6], [])
        cell_se, cell_sy = cell['se'], cell['sy']
        for j in range(len(cell_se)):
            sy = cell_sy[j]
            if sy > 0.0:
                values.append(float(np.sqrt(np.float64(cell_se[j]) / np.float64(sy))))
        # a mask whose every component has zero truth energy keeps its empty list
    return {seed: float(np.mean(np.asarray(values, float)))
            for seed, values in by_mask.items() if values}


def mask_macro_nrmse(acc, method, protocol, ratio=AUTO, segment=DEFAULT_SEGMENT,
                     training_seed=AUTO, index=None):
    """The manuscript score for one (method, protocol, ratio, segment) cell.

    ``None`` when the condition has no records or no component group with
    positive truth energy (the manuscript prints ``--`` for those).  ``ratio``
    defaults to :data:`AUTO`, i.e. ``None`` for ``width`` and 0.3 otherwise;
    ``training_seed`` defaults to :data:`AUTO` (see :func:`resolve_seed`).
    """
    scores = mask_scores(acc, method, protocol, ratio, segment, training_seed, index)
    if not scores:
        return None
    return float(np.mean(np.asarray(list(scores.values()), float)))


def score_grid(acc, methods, protocols, ratio=AUTO, segment=DEFAULT_SEGMENT, training_seed=AUTO):
    """Convenience: ``{(method, protocol): value}`` for a method/protocol grid."""
    return {(method, protocol): mask_macro_nrmse(acc, method, protocol, ratio, segment, training_seed)
            for method in methods for protocol in protocols}


# ---------------------------------------------------------------------------
# Serialisation (JSON cache; keys are strings, ratio null is preserved)
# ---------------------------------------------------------------------------

def accumulator_payload(acc, meta=None):
    """JSON-ready dict; insertion order (and therefore summation order) kept."""
    if not isinstance(acc, dict):
        raise TypeError('acc must be an accumulator dict')
    cells = {}
    for key, cell in acc.items():
        if len(key) != len(KEY_FIELDS):
            raise ValueError(f'accumulator key has {len(key)} fields, expected {len(KEY_FIELDS)}')
        string_key = json.dumps(list(key), separators=(',', ':'))
        if string_key in cells:
            raise ValueError(f'duplicate serialised key {string_key}')
        cells[string_key] = {'n': cell['n'], 'se': list(cell['se']), 'sy': list(cell['sy'])}
    payload = {'format': ACC_FORMAT, 'key_fields': list(KEY_FIELDS), 'cells': cells}
    if meta is not None:
        payload['meta'] = meta
    return payload


def accumulator_from_payload(payload):
    """Inverse of :func:`accumulator_payload`; validates the format tag."""
    if not isinstance(payload, dict) or payload.get('format') != ACC_FORMAT:
        raise ValueError(f'not a {ACC_FORMAT} payload')
    if tuple(payload.get('key_fields', ())) != tuple(KEY_FIELDS):
        raise ValueError('accumulator key layout mismatch; refusing to reinterpret')
    acc = {}
    for string_key, value in payload['cells'].items():
        key = tuple(json.loads(string_key))
        if len(key) != len(KEY_FIELDS):
            raise ValueError(f'accumulator key has {len(key)} fields, expected {len(KEY_FIELDS)}')
        if set(value) != {'n', 'se', 'sy'}:
            raise ValueError(f'unexpected accumulator payload fields for {string_key}: {sorted(value)}')
        acc[key] = {'n': int(value['n']), 'se': [float(x) for x in value['se']],
                    'sy': [float(x) for x in value['sy']]}
    return acc


def save_accumulator(acc, path, meta=None):
    """Write the cache (compact JSON) with exclusive create: never overwrites."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        json.dump(accumulator_payload(acc, meta=meta), handle, separators=(',', ':'),
                  allow_nan=False)
        handle.write('\n')
    return path


def load_accumulator(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'accumulator cache not found: {path}')
    return accumulator_from_payload(json.loads(path.read_text()))


def baseline_with(new_records, cache=CACHE_DIR / CACHE_NAME, stats=None):
    """Frozen public baseline plus a new model's records, in one accumulator.

    The intended use for a follow-up model: its records land under its own
    ``method`` name, so the frozen baseline's keys are untouched by the merge
    and both can be scored with the same :func:`mask_macro_nrmse` call.
    """
    acc = load_accumulator(cache)
    add_records(acc, new_records, stats=stats)
    return acc


# ---------------------------------------------------------------------------

def main():
    """Verify final-paper records instead of obsolete hard-coded snapshots."""
    import runpy
    runpy.run_path(str(ROOT / 'scripts/verify_final_paper.py'), run_name='__main__')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
