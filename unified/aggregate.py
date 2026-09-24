"""Exact reproduction of the DATE-v3 "mean-mask macro NRMSE" aggregation.

The manuscript's principal accuracy table (``paper/round3_date_v3/main.tex``,
Table 1 / ``tab:completion``, and Table 2 / ``tab:transfer``) reports numbers
that are reproduced, digit for digit, from the frozen per-record error files by
the single recipe implemented here.  The recipe is not re-derived from the
paper prose: it is transcribed from the frozen producer,

    pdkcap-v0/scripts/report_round3_uncertainty_v2.py      (sha256 997b16e8...)
      -> runs/round3_uncertainty_<cohort>_v2/report.json   "macro" rows
    pdkcap-v0/scripts/collect_round3_results_v2.py
      -> runs/round3_result_collection_v1/summary.json     cohort "macro" rows
    pdkcap-v0/paper/round3_date_v2/build_assets.py
      -> paper/round3_date_v2/RESULT_SNAPSHOT.json         manuscript numbers

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

Run ``python -m unified.aggregate`` (from ``test-v1``) for the self-test: it
reproduces every published cell of both accuracy tables to 1e-9, cross-checks
the hardcoded table against ``RESULT_SNAPSHOT.json``, checks that the
accumulator covers each frozen ``population.json`` cell exactly (no silent
skipping), and exercises the merge path used for a new model.  The public
cohort is streamed once and cached (exclusive create: the cache is never
overwritten); ``receipt.json`` next to it records the source sha256, byte size,
record count and elapsed seconds, and is refreshed whenever the cache is
regenerated.
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
    'public': ARCHIVE / 'runs/round3_fixed_public_retrospective_original_v1',
    'reference': ARCHIVE / 'runs/round3_fixed_reference_confirmation_round3_main_v1',
    'to_asap7': ARCHIVE / 'runs/round3_fixed_to_asap7_confirmation_round3_main_v1',
    'to_freepdk15': ARCHIVE / 'runs/round3_fixed_to_freepdk15_confirmation_round3_main_v1',
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

SNAPSHOT = ARCHIVE / 'paper/round3_date_v2/RESULT_SNAPSHOT.json'

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
# Self-test: every published cell, to 1e-9
# ---------------------------------------------------------------------------

TOLERANCE = 1e-9

#: Copied verbatim from ``paper/round3_date_v2/RESULT_SNAPSHOT.json``
#: (``manuscript_completion``: public_30pct = Random/Block/Extrap.,
#: reference_confirmation = Random/Block/Extrap./Width; the transfer table uses
#: the same four columns).  ``None`` = the manuscript prints ``--``.
EXPECTED_PUBLIC = {
    'linear': ('classical', (0.23619653634959198, 0.685228471848708, 1.1867145174513043)),
    'pchip': ('classical', (0.21549729811388976, 0.6483952498212586, 1.1867145174513043)),
    'gp': ('classical', (0.49318867354306856, 2.2353384074727107, 4.679959355449726)),
    'original_dro': ('ensemble', (0.16519275658905594, 0.23566924535640563, 0.2885741791749423)),
    'retrained_dro': ('ensemble', (0.16519275595680927, 0.23566924353308308, 0.2885741755857567)),
    'hard_local': ('ensemble', (0.15254251253946993, 0.2298860798599463, 0.2885741791749423)),
    'gated_none': ('ensemble', (0.1724412959965748, 0.36924971231070197, 0.5515777686574208)),
    'fixed': ('deterministic', (0.14706287282520025, 0.2246175096935909, 0.2885741791749423)),
    'risk': ('ensemble', (0.16728765501486284, 0.31799786215059006, 0.4726541053525402)),
    'top2': ('ensemble', (0.16626883330110168, 0.3199400236660559, 0.4841879335417084)),
}
EXPECTED_REFERENCE = {
    'linear': ('classical', (0.025565749800677606, 0.16311495755792302,
                             0.5662870781836279, 0.011583260714024744)),
    'pchip': ('classical', (None, None, None, None)),
    'gp': ('classical', (0.01199698345606333, 3.463248266327322,
                         17.67577474994804, 0.008667633696319139)),
    'original_dro': ('ensemble', (0.06153043765405604, 0.15558688260338951,
                                  0.291678507440412, 0.059165730330992886)),
    'retrained_dro': ('ensemble', (0.032990826702690504, 0.09776025389855605,
                                   0.19490318969991172, 0.027563948309404982)),
    'hard_local': ('ensemble', (0.05029407631718449, 0.13783596154833944,
                                0.291678507440412, 0.03639710837648118)),
    'gated_none': ('ensemble', (0.02069566817961864, 0.08652521985398445,
                                0.1588897105180227, 0.019673512140246166)),
    'fixed': ('deterministic', (0.02184942786741777, 0.09062031996172759,
                                0.291678507440412, 0.01897080931620787)),
    'risk': ('ensemble', (0.011428025222934454, 0.09543011620430061,
                          0.20677367723541534, 0.006869613054851667)),
    'top2': ('ensemble', (0.011146174173966883, 0.09358422789914841,
                          0.20542584783925294, 0.006732053157818137)),
}
EXPECTED_TRANSFER = {
    'to_asap7': {
        'linear': ('classical', (0.025161660133242066, 0.15895170468509945,
                                 0.5579941567813385, 0.011564609428700672)),
        'original_dro': ('ensemble', (0.04191895622214814, 0.09251751210257712,
                                      0.1814492850862071, 0.041551197454714306)),
        'retrained_dro': ('ensemble', (0.060515891267731214, 0.13538334999786691,
                                       0.23115988866248172, 0.05081908854431216)),
        'hard_local': ('ensemble', (0.0368460887305113, 0.08520548134872714,
                                    0.1814492850862071, 0.029112955979845416)),
        'gated_none': ('ensemble', (0.023080195106686345, 0.07752244629198632,
                                    0.14446836998149676, 0.020830590892731527)),
        'fixed': ('deterministic', (0.02380375041711972, 0.07778252919231325,
                                    0.1814492850862071, 0.015359996227579688)),
        'risk': ('ensemble', (0.012681857172420846, 0.11941998294170894,
                              0.25186483311528834, 0.006269875753298081)),
        'top2': ('ensemble', (0.012137889324780948, 0.11731466514449566,
                              0.2516153144812281, 0.0061512692916964925)),
    },
    'to_freepdk15': {
        'linear': ('classical', (0.025969839468113144, 0.16727821043074662,
                                 0.5745799995859172, 0.011601911999348813)),
        'original_dro': ('ensemble', (0.16450601992081262, 0.23766837270793983,
                                      0.36494569480989775, 0.14195877450981184)),
        'retrained_dro': ('ensemble', (0.16133016146904383, 0.24595294531596662,
                                       0.40568995916467926, 0.14272642397212792)),
        'hard_local': ('ensemble', (0.06458213975012297, 0.14302797707029294,
                                    0.36494569480989775, 0.06600998838743116)),
        'gated_none': ('ensemble', (0.06105021483085381, 0.1390909790313512,
                                    0.20187674614748524, 0.0472565190812881)),
        'fixed': ('deterministic', (0.047658777649458736, 0.11669230966823178,
                                    0.36494569480989775, 0.035443456234368606)),
        'risk': ('ensemble', (0.022955509134210933, 0.11334550705893076,
                              0.2832127432584326, 0.010726577665078374)),
        'top2': ('ensemble', (0.02292441768821296, 0.11319159414945794,
                              0.28189199137363524, 0.010695585282713346)),
    },
}
PROTOCOLS4 = ('mcar', 'block', 'extrapolation', 'width')
PROTOCOLS3 = ('mcar', 'block', 'extrapolation')

#: Cross-check that the hardcoded table above still equals the frozen snapshot.
SNAPSHOT_KEYS = {
    'public': ('manuscript_completion', 'public_30pct'),
    'reference': ('manuscript_completion', 'reference_confirmation'),
    'to_asap7': ('manuscript_transfer', 'to_asap7'),
    'to_freepdk15': ('manuscript_transfer', 'to_freepdk15'),
}


def _snapshot_table(domain):
    payload = json.loads(SNAPSHOT.read_text())
    section, field = SNAPSHOT_KEYS[domain]
    return {row['method']: (None, tuple(row[field])) for row in payload[section]}


def check(domain, acc, expected, protocols, results):
    """Compare one cohort against its published cells; append PASS/FAIL rows."""
    table = {method: (seed, values) for method, (seed, values) in expected.items()}
    if domain in SNAPSHOT_KEYS:
        snapshot = _snapshot_table(domain)
        for method, (_, values) in table.items():
            published = snapshot.get(method, (None, None))[1]
            results.append(('snapshot', domain, method, values, published,
                            published == values, True))
    index = condition_index(acc)
    seeds = {}
    for key in acc:
        seeds.setdefault(key[0], set()).add(key[1])
    for method, (seed, values) in table.items():
        # the seed recorded in the snapshot must be the seed actually used.
        # A method that is absent from the cohort altogether (PCHIP has no
        # multiwidth tables) is legitimately all-None and has no seed to check.
        present = sorted(seeds.get(method, set()))
        if present and seed not in present:
            results.append((domain, method, 'training_seed', seed, present, False, False))
        for protocol, want in zip(protocols, values):
            got = mask_macro_nrmse(acc, method, protocol, training_seed=seed, index=index)
            if want is None:
                absent = (method, seed, protocol, resolve_ratio(protocol),
                          DEFAULT_SEGMENT) not in index
                ok = got is None and absent
            else:
                ok = got is not None and abs(got - want) <= TOLERANCE
            results.append((domain, method, protocol, want, got, ok, got is None and want is None))


def check_coverage(accs, results):
    """Structural check: no scored cell was silently skipped.

    Each frozen run directory ships ``population.json``, the expected query
    population per (process, family, protocol, ratio, mask_seed, segment).  For
    every published table cell the accumulated (process, family, mask_seed) set
    must equal that population exactly -- no missing cells, no phantom cells.
    """
    for domain, expected in (('public', EXPECTED_PUBLIC), ('reference', EXPECTED_REFERENCE)):
        if domain not in accs:
            continue
        acc = accs[domain]
        population = json.loads((COHORTS[domain] / 'population.json').read_text())
        wanted = {}
        for row in population:
            wanted.setdefault((row['protocol'], row['ratio'], row['segment']), set()).add(
                (row['process'], row['family'], row['mask_seed']))
        index = condition_index(acc)
        for method, (seed, values) in expected.items():
            for protocol, want in zip(PROTOCOLS4 if domain == 'reference' else PROTOCOLS3, values):
                if want is None and not seeds_for(acc, method):
                    continue
                key = (protocol, resolve_ratio(protocol), DEFAULT_SEGMENT)
                if key not in wanted:
                    continue
                cells = index.get((method, seed, key[0], key[1], key[2]), {})
                got = {(k[2], k[3], k[6]) for keys in cells.values() for k in keys}
                ok = got == wanted[key]
                results.append((f'coverage:{domain}', method, protocol,
                                f'{len(wanted[key])} cells', f'{len(got)} cells', ok, True))


MERGE_RTOL = 1e-12


def _close(a, b, rtol=MERGE_RTOL):
    return abs(a - b) <= rtol * max(abs(a), abs(b), 1e-300)


def check_merge(results):
    """End-to-end check of :func:`add_records` / :func:`merge_accumulators`.

    Streaming the same cohort twice must double every ``n``/``se``/``sy`` and
    leave every mask score unchanged.  Doubling is *not* bit-exact here: the
    second pass continues the same running sum in a different association order
    (``((S+x1)+x2)...`` vs ``((x1+x2)+x3)...``), so the totals agree to one ulp
    of the running sum, ~1e-16 relative, and the scores to the same order.  The
    comparison therefore uses :data:`MERGE_RTOL`; the reproducibility checks
    against the published table stay at 1e-9 absolute.
    """
    acc = stream_records(COHORTS['reference'])
    doubled = {}
    add_records(doubled, COHORTS['reference'])
    add_records(doubled, COHORTS['reference'])
    sums_ok = set(acc) == set(doubled)
    if sums_ok:
        for key, cell in acc.items():
            other = doubled[key]
            if other['n'] != 2 * cell['n']:
                sums_ok = False
                break
            for field in ('se', 'sy'):
                if any(not _close(other[field][j], 2 * cell[field][j])
                       for j in range(len(cell['se']))):
                    sums_ok = False
                    break
    results.append(('merge', 'reference', 'add_records ~doubles n/se/sy',
                    f'2x (rtol {MERGE_RTOL:g})', f'2x (rtol {MERGE_RTOL:g})', sums_ok, True))
    same = True
    for method in ('linear', 'fixed', 'risk'):
        for protocol in PROTOCOLS4:
            left = mask_scores(acc, method, protocol)
            right = mask_scores(doubled, method, protocol)
            if left.keys() != right.keys() or any(not _close(left[k], right[k]) for k in left):
                same = False
    results.append(('merge', 'reference', 'mask scores invariant under merge',
                    f'equal (rtol {MERGE_RTOL:g})', f'equal (rtol {MERGE_RTOL:g})', same, True))
    merged = merge_accumulators(acc, acc)
    agree = set(merged) == set(doubled)
    if agree:
        for key, cell in merged.items():
            other = doubled[key]
            if cell['n'] != other['n'] or any(
                    not _close(cell[field][j], other[field][j])
                    for field in ('se', 'sy') for j in range(len(cell['se']))):
                agree = False
                break
    results.append(('merge', 'reference', 'merge_accumulators matches add_records',
                    f'equal (rtol {MERGE_RTOL:g})', f'equal (rtol {MERGE_RTOL:g})', agree, True))


def report(results):
    labels = [f'{row[0]} | {row[1]} | {row[2]}' for row in results]
    width = max(len(label) for label in labels) + 2
    failures = 0
    for label, (domain, method, protocol, want, got, ok, _skipped) in zip(labels, results):
        if want is None and got is None:
            detail = 'undefined (--)'
        elif isinstance(want, (int, float)) and isinstance(got, (int, float)):
            detail = f'want {want!r} got {got!r} delta {abs(got - want):.3e}'
        else:
            detail = f'want {want!r} got {got!r}'
        status = 'PASS' if ok else 'FAIL'
        if not ok:
            failures += 1
        print(f'{status:4s} {label:<{width}}{detail}')
    print(f'--- {len(results) - failures}/{len(results)} checks passed, {failures} failed')
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--cache', type=Path, default=CACHE_DIR / CACHE_NAME,
                        help='public-cohort accumulator cache (loaded if present)')
    parser.add_argument('--restream', action='store_true',
                        help='ignore an existing cache and re-stream the public cohort')
    parser.add_argument('--skip-public', action='store_true',
                        help='test only the three confirmation cohorts')
    parser.add_argument('--no-cache-write', action='store_true',
                        help='do not create the cache directory')
    args = parser.parse_args(argv)

    results = []
    accs = {}
    for domain in ('reference', 'to_asap7', 'to_freepdk15'):
        started = time.perf_counter()
        accs[domain] = stream_records(COHORTS[domain])
        print(f'[stream] {domain:<12} {len(accs[domain]):>8} cell keys '
              f'{time.perf_counter() - started:.1f}s', flush=True)

    cache_stats = None
    if not args.skip_public:
        accelerator = load_accumulator(args.cache) if args.cache.exists() and not args.restream else None
        if accelerator is not None:
            accs['public'] = accelerator
            print(f'[cache ] public       {len(accelerator):>8} cell keys from {args.cache}', flush=True)
        else:
            stats = {}
            started = time.perf_counter()
            accs['public'] = stream_records(COHORTS['public'], stats=stats)
            stats['elapsed_seconds'] = time.perf_counter() - started
            print(f'[stream] public       {len(accs["public"]):>8} cell keys '
                  f'{stats["elapsed_seconds"]:.1f}s', flush=True)
            if not args.no_cache_write:
                save_accumulator(accs['public'], args.cache, meta={
                    'cohort': 'public',
                    'run': str(COHORTS['public']),
                    'records': stats['path'],
                    'records_sha256': file_hash(Path(stats['path'])),
                    'records_bytes': stats['bytes'],
                    'records_streamed': stats['records'],
                    'elapsed_seconds': stats['elapsed_seconds'],
                    'source_sha256': file_hash(Path(__file__)),
                    'macro_order': list(MACRO_ORDER),
                })
                print(f'[cache ] wrote {args.cache}', flush=True)
                cache_stats = stats

    if 'public' in accs:
        check('public', accs['public'], EXPECTED_PUBLIC, PROTOCOLS3, results)
    else:
        print('[skip  ] public cohort checks (--skip-public)')
    check('reference', accs['reference'], EXPECTED_REFERENCE, PROTOCOLS4, results)
    check('to_asap7', accs['to_asap7'], EXPECTED_TRANSFER['to_asap7'], PROTOCOLS4, results)
    check('to_freepdk15', accs['to_freepdk15'], EXPECTED_TRANSFER['to_freepdk15'], PROTOCOLS4, results)
    check_coverage(accs, results)
    check_merge(results)
    failures = report(results)
    print('RESULT: ' + ('PASS' if not failures else f'FAIL ({failures})'))

    if cache_stats is not None and not args.no_cache_write:
        receipt = args.cache.parent / RECEIPT_NAME
        producer = ARCHIVE / 'scripts/report_round3_uncertainty_v2.py'
        # The receipt describes the cache that was just streamed, so it is
        # rewritten on every regeneration; the cache itself is exclusive-create.
        with receipt.open('w') as handle:
            json.dump({
                'cohort': 'public',
                'run': str(COHORTS['public']),
                'source_records': cache_stats['path'],
                'source_records_sha256': file_hash(Path(cache_stats['path'])),
                'source_records_bytes': cache_stats['bytes'],
                'records_streamed': cache_stats['records'],
                'elapsed_seconds': cache_stats['elapsed_seconds'],
                'cell_keys': len(accs['public']),
                'cache': str(args.cache),
                'cache_sha256': file_hash(args.cache),
                'aggregation_source': str(producer),
                'aggregation_source_sha256': file_hash(producer) if producer.exists() else None,
                'module_sha256': file_hash(Path(__file__)),
                'macro_order': list(MACRO_ORDER),
                'tolerance': TOLERANCE,
                'checks_total': len(results),
                'checks_failed': failures,
                'selftest': 'PASS' if not failures else 'FAIL',
                'python': sys.version.split()[0],
                'numpy': np.__version__,
            }, handle, indent=2, allow_nan=False)
            handle.write('\n')
        print(f'[cache ] wrote {receipt}', flush=True)
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
