"""Paired comparison of the unified network against the frozen DATE-v3 baselines.

Baseline evidence is the archived per-record file of the frozen cohort; the new
model's evidence is produced by :mod:`unified.score` in the identical schema.
Both are aggregated by the single verified recipe in :mod:`unified.aggregate`,
so a reported difference is a difference in the estimator, not in the metric
path.  Accumulators are cached per cohort under ``runs/accum_v1``.
"""
import argparse
import json
import time
from pathlib import Path

from .aggregate import (COHORTS, add_records, load_accumulator, mask_macro_nrmse,
                        save_accumulator, stream_records)
from .workspace import ROOT, file_hash, new_run, write_json

CACHE = ROOT / 'runs/accum_v1'
CACHE.mkdir(parents=True, exist_ok=True)

#: Manuscript display names for the frozen comparison methods.
BASELINES = [('linear', 'Linear'), ('pchip', 'PCHIP'), ('gp', 'GP'),
             ('retrained_dro', 'Retrained residual'), ('hard_local', 'Local clamp'),
             ('gated_none', 'Gated'), ('fixed', 'SACE-Select'),
             ('risk', 'SACE-Risk'), ('top2', 'SACE-Mix')]
PROTOCOLS = (('mcar', 'Random'), ('block', 'Block'), ('extrapolation', 'Extrap.'))


def cohort_accumulator(name, extra_paths=()):
    """Baseline cohort accumulator plus any new-model record files, cached."""
    tag = name + ''.join('_' + Path(p).parent.name for p in extra_paths)
    cache = CACHE / f'{tag}.json'
    if cache.exists():
        return load_accumulator(cache)
    path = COHORTS[name]
    if path.is_dir():
        path = path / 'records.jsonl.gz'
    started = time.perf_counter()
    accumulator = stream_records(path)
    for extra in extra_paths:
        add_records(accumulator, extra)
    save_accumulator(accumulator, cache, meta=dict(cohort=name, source=str(path),
                                                   source_sha256=file_hash(path),
                                                   extras=[str(p) for p in extra_paths],
                                                   seconds=time.perf_counter() - started))
    return accumulator


def table(accumulator, methods, protocols=PROTOCOLS, ratio=.3, segment='all'):
    rows = []
    for key, label in methods:
        scores = [mask_macro_nrmse(accumulator, key, protocol, ratio, segment)
                  for protocol, _ in protocols]
        rows.append(dict(method=key, label=label,
                         scores=[None if value is None else float(value) for value in scores]))
    return rows


def render(rows, protocols=PROTOCOLS, title=''):
    head = f"{'method':22s}" + ''.join(f'{label:>12s}' for _, label in protocols)
    lines = [title, head, '-' * len(head)]
    for row in rows:
        cells = ''.join('           --' if value is None else f'{value:12.4f}' for value in row['scores'])
        lines.append(f"{row['label']:22s}{cells}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', choices=sorted(COHORTS), required=True)
    parser.add_argument('--records', type=Path, nargs='+', required=True)
    parser.add_argument('--segment', default='all')
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()
    accumulator = cohort_accumulator(args.cohort, args.records)
    own = [('sace_r', 'SACE-R (unified)'), ('sace_r_anchor', '  . anchor only')]
    rows = table(accumulator, [*BASELINES, *own], segment=args.segment)
    rendered = render(rows, title=f'cohort={args.cohort} segment={args.segment} macro NRMSE (lower better)')
    print(rendered)
    if args.output:
        output = new_run(args.output)
        write_json(output / 'COMPLETED.json', dict(cohort=args.cohort, segment=args.segment,
                                                   records=[str(p) for p in args.records], rows=rows,
                                                   rendered=rendered))
        print(f'\nwritten to {output}')


if __name__ == '__main__':
    main()
