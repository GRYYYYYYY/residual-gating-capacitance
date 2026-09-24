"""Frozen configuration, reported on every cohort with one aggregation.

Reads the archived per-record evidence of the frozen DATE-v3 cohorts and the new
model's records, aggregates both with the single verified mask-macro recipe, and
prints the comparison table plus paired group-bootstrap intervals where the
cohort has associated groups.  No configuration choice happens here.
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, mask_macro_nrmse, stream_records  # noqa: E402
from unified.paired import bootstrap_delta, group_accumulator, prepare  # noqa: E402
from unified.workspace import ARCHIVE, new_run, write_json  # noqa: E402

BASELINE_DIRS = {
    ('public', 'confirmation'): 'round3_fixed_public_retrospective_original_v1',
    ('reference', 'confirmation'): 'round3_fixed_reference_confirmation_round3_main_v1',
    ('to_asap7', 'confirmation'): 'round3_fixed_to_asap7_confirmation_round3_main_v1',
    ('to_freepdk15', 'confirmation'): 'round3_fixed_to_freepdk15_confirmation_round3_main_v1',
    ('to_asap7', 'boundary'): 'round3_fixed_to_asap7_boundary_round3_edge_v1',
    ('to_freepdk15', 'boundary'): 'round3_fixed_to_freepdk15_boundary_round3_edge_v1',
    ('reference', 'boundary'): 'round3_fixed_reference_boundary_round3_edge_v1',
}
FROZEN_VAL = {name: f'runs/frozen_val_records_{name}_v1/records.jsonl.gz'
              for name in ('public', 'reference', 'to_asap7', 'to_freepdk15')}
LABELS = [('linear', 'Linear'), ('pchip', 'PCHIP'), ('gp', 'GP'),
          ('retrained_dro', 'Retrained residual'), ('original_dro', 'Residual ensemble'),
          ('hard_local', 'Local clamp'), ('gated_none', 'Gated'),
          ('fixed', 'SACE-Select'), ('risk', 'SACE-Risk'), ('top2', 'SACE-Mix')]
PROTOCOLS = (('mcar', 'Random'), ('block', 'Block'), ('extrapolation', 'Extrap.'))


def score_table(accumulator, method, method_label):
    rows = []
    for key, label in [*LABELS, (method, method_label)]:
        values = [mask_macro_nrmse(accumulator, key, protocol, .3) for protocol, _ in PROTOCOLS]
        width = mask_macro_nrmse(accumulator, key, 'width', None)
        rows.append(dict(method=key, label=label, scores=values, width=width))
    return rows


def render(rows, title):
    head = f"{'method':22s}" + ''.join(f'{label:>12s}' for _, label in PROTOCOLS) + f"{'Width':>12s}"
    lines = [title, head, '-' * len(head)]
    for row in rows:
        cells = ''.join('          --' if value is None else f'{value:12.4f}' for value in row['scores'])
        cells += '          --' if row['width'] is None else f'{row["width"]:12.4f}'
        lines.append(f"{row['label']:22s}{cells}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', required=True)
    parser.add_argument('--cohort', required=True, choices=['val', 'confirmation', 'boundary'])
    parser.add_argument('--records', type=Path, nargs='+', required=True)
    parser.add_argument('--method', required=True)
    parser.add_argument('--label', default='SACE-R (unified)')
    parser.add_argument('--bootstrap', action='store_true')
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()

    if args.cohort == 'val':
        baseline = ROOT / FROZEN_VAL[args.domain]
    else:
        baseline = ARCHIVE / 'runs' / BASELINE_DIRS[(args.domain, args.cohort)]
    accumulator = stream_records(baseline / 'records.jsonl.gz')
    for path in args.records:
        add_records(accumulator, path)
    rows = score_table(accumulator, args.method, args.label)
    title = f'{args.domain} / {args.cohort}   mean-mask macro NRMSE (lower is better)'
    print(render(rows, title))

    intervals = []
    if args.bootstrap:
        methods = [args.method, 'fixed', 'linear']
        grouped = group_accumulator([baseline / 'records.jsonl.gz', *args.records], methods)
        for protocol, _ in PROTOCOLS:
            prepared = prepare(grouped, protocol, .3)
            for reference in ('fixed', 'linear'):
                result = bootstrap_delta(prepared, args.method, reference, replicates=2000)
                intervals.append(result)
                print(f"  {protocol:14s} vs {reference:6s} delta {result['delta']:+.5f} "
                      f"[{result['low']:+.5f}, {result['high']:+.5f}]  "
                      f"P(better)={result['probability_better']:.3f}  n_groups={result['group_count']}")
    if args.output:
        output = new_run(args.output)
        write_json(output / 'COMPLETED.json', dict(domain=args.domain, cohort=args.cohort,
                                                   method=args.method, rows=rows,
                                                   intervals=intervals, rendered=render(rows, title),
                                                   records=[str(p) for p in args.records],
                                                   scope='aggregation only; no selection'))
        print(f'\nwritten to {output}')


if __name__ == '__main__':
    main()
