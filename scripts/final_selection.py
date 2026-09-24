"""Choose one configuration per domain on the validation cohort.

The deployment question is "how bad is the worst thing this model does", so the
selection rule is the one the training objective optimizes: among candidate
checkpoint sets it takes the one whose **largest** validation cell is smallest,
over every measured cell -- both regimes, both missingness protocols used for
scoring, and all four missing rates -- rather than the smallest average.  An
average over cells is dominated by the single worst regime and therefore
selects almost entirely on extrapolation; the maximum spends the whole
candidate set on the cell that would fail first.

The validation cohort is the only cohort this reads.  Confirmation cohorts are
opened afterwards, once, with the selection frozen.
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, condition_index, mask_macro_nrmse  # noqa: E402
from unified.regime import regroup  # noqa: E402
from unified.workspace import new_run, write_json  # noqa: E402

RATIOS = (0.1, 0.3, 0.5, 0.7)
PROTOCOLS = ('mcar', 'block', 'extrapolation')
REGIMES = ('inside', 'outside')


def cells_of(group, method):
    """Every measured validation cell of one candidate."""
    values = {}
    for regime in REGIMES:
        for protocol in PROTOCOLS:
            for ratio in RATIOS:
                value = mask_macro_nrmse(group, method, protocol, ratio)
                if value is not None:
                    values[f'{regime}/{protocol}/{ratio:.1f}'] = value
    if not values:
        raise ValueError(f'no defined cell for {method}')
    return values


def summarize(values, rule):
    if rule == 'max':
        key = max(values, key=lambda name: values[name])
        return dict(score=values[key], cell=key, cells=values)
    return dict(score=sum(values.values()) / len(values), cell=f'{len(values)} cells',
                cells=values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', required=True)
    parser.add_argument('--records', type=Path, nargs='+', required=True,
                        help='validation records, one per candidate')
    parser.add_argument('--method', nargs='+', required=True)
    parser.add_argument('--rule', choices=('mean', 'max'), default='mean')
    parser.add_argument('--output', type=str, default=None)
    parser.add_argument('--print-cells', action='store_true')
    args = parser.parse_args()
    if len(args.records) != len(args.method):
        raise ValueError('records and method must line up')

    accumulator = {}
    for path in args.records:
        add_records(accumulator, path)
    grouped = regroup(accumulator)
    rows = []
    for path, method in zip(args.records, args.method):
        # A candidate is judged over both regimes; the two regimes' cell sets are
        # then pooled, so neither is allowed to hide the other.
        merged = {}
        for regime in REGIMES:
            for name, value in cells_of(grouped[regime], method).items():
                merged[f'{regime}/{name}'] = value
        rows.append(dict(method=method, records=str(path), summary=summarize(merged, args.rule)))
    rows.sort(key=lambda row: row['summary']['score'])
    print(f'--- {args.domain}: {"mean" if args.rule == "mean" else "maximum"} validation cell '
          f'over both regimes, both protocols and all four missing rates')
    for row in rows:
        summary = row['summary']
        print(f"  {row['method']:26s} {summary['score']:.4f}   worst {summary['cell']}")
        if args.print_cells:
            for name, value in sorted(summary['cells'].items(), key=lambda item: -item[1])[:3]:
                print(f'      {name:24s} {value:.4f}')
    chosen = rows[0]
    print(f"  selected: {chosen['method']} ({chosen['records']})")
    if args.output:
        output = new_run(args.output)
        write_json(output / 'COMPLETED.json', dict(
            domain=args.domain,
            rule=f'smallest {args.rule} validation cell over both regimes, both protocols '
                 'and all four missing rates',
            selected=chosen['method'], selected_records=chosen['records'],
            selected_summary=chosen['summary'], cohorts_read=['validation'],
            confirmation_cohorts_read=[],
            candidates=[dict(method=row['method'], records=row['records'],
                             summary=row['summary']) for row in rows]))
        print(f'  written to {output}')


if __name__ == '__main__':
    main()
