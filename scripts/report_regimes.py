"""Report every method by interpolation regime on one cohort.

`docs/baseline.md` compares the interpolation step, and the question that step
answers is either "bracket a query inside the characterized range" or "answer
beyond it".  This script rebuilds every method's evidence on one cohort,
collapses the five support regions into those two regimes, and prints the
verified mean-mask macro NRMSE for each -- plus the paired group bootstrap
against the strongest classical baseline.
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
from unified.regime import REGIMES, regroup  # noqa: E402
from unified.workspace import ARCHIVE, new_run, write_json  # noqa: E402

FROZEN = {
    ('public', 'validation'): ('frozen_val_records_public_v1', None),
    ('public', 'confirmation'): (None, 'round3_fixed_public_retrospective_original_v1'),
    ('reference', 'validation'): ('frozen_val_records_reference_v1', None),
    ('reference', 'confirmation'): (None, 'round3_fixed_reference_confirmation_round3_main_v1'),
    ('reference', 'boundary'): (None, 'round3_fixed_reference_boundary_round3_edge_v1'),
    ('to_asap7', 'validation'): ('frozen_val_records_to_asap7_v1', None),
    ('to_asap7', 'confirmation'): (None, 'round3_fixed_to_asap7_confirmation_round3_main_v1'),
    ('to_asap7', 'boundary'): (None, 'round3_fixed_to_asap7_boundary_round3_edge_v1'),
    ('to_freepdk15', 'validation'): ('frozen_val_records_to_freepdk15_v1', None),
    ('to_freepdk15', 'confirmation'): (None, 'round3_fixed_to_freepdk15_confirmation_round3_main_v1'),
    ('to_freepdk15', 'boundary'): (None, 'round3_fixed_to_freepdk15_boundary_round3_edge_v1'),
}
CLASSICAL = [('cmi1d', 'CMI-1D'), ('cmi2d', 'CMI-2D'), ('cmi4d', 'CMI-4D'),
             ('openrcx_li', 'OpenRCX-LI'), ('pchip', 'PCHIP'), ('idw', 'IDW'), ('gp', 'GP')]
PRIOR = [('fixed', 'SACE-Select'), ('risk', 'SACE-Risk'), ('top2', 'SACE-Mix'),
         ('original_dro', 'Residual'),
         ('linear', 'Simplex linear'), ('hard_local', 'Local clamp'), ('gated_none', 'Gated')]
PROTOCOLS = (('mcar', 'Random'), ('block', 'Block'), ('extrapolation', 'Extrap.'))


def frozen_records(domain, cohort):
    val, fixed = FROZEN[(domain, cohort)]
    if val is not None:
        return ROOT / 'runs' / val / 'records.jsonl.gz'
    return ARCHIVE / 'runs' / fixed / 'records.jsonl.gz'


def regime_accumulator(accumulator, regime):
    return regroup(accumulator)[regime]


def render(rows, protocols, extras, title):
    head = f"{'method':22s}" + ''.join(f'{label:>12s}' for _, label in protocols) \
           + ''.join(f'{label:>12s}' for label, _ in extras) + f"{'mean':>10s}"
    lines = [title, head, '-' * len(head)]
    for row in rows:
        cells = ''.join('          --' if value is None else f'{value:12.4f}'
                        for value in row['scores'])
        cells += ''.join('          --' if value is None else f'{value:12.4f}'
                         for value in row['extras'])
        lines.append(f"{row['label']:22s}{cells}{row['mean']:10.4f}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', required=True)
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--baseline-records', type=Path, required=True)
    parser.add_argument('--unified-records', type=Path, required=True)
    parser.add_argument('--unified-method', required=True)
    parser.add_argument('--unified-label', default='Unified (ours)')
    parser.add_argument('--ratio', type=float, default=.3)
    parser.add_argument('--bootstrap', action='store_true')
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()

    accumulator = stream_records(frozen_records(args.domain, args.cohort))
    add_records(accumulator, args.baseline_records)
    add_records(accumulator, args.unified_records)
    regimes = regroup(accumulator)

    entries = [*CLASSICAL, (args.unified_method, args.unified_label), *PRIOR]
    payload = {}
    for name, group in regimes.items():
        rows = []
        for method, label in entries:
            scores = [mask_macro_nrmse(group, method, protocol, args.ratio)
                      for protocol, _ in PROTOCOLS]
            if all(value is None for value in scores):
                continue
            width = mask_macro_nrmse(group, method, 'width', None)
            present = [value for value in scores if value is not None]
            rows.append(dict(method=method, label=label, scores=scores, width=width,
                             mean=float(sum(present) / len(present)) if present else None))
        show_width = any(row['width'] is not None for row in rows)
        rows.sort(key=lambda row: (row['mean'] is None, row['mean']))
        columns = [('Width', 'width')] if show_width else []
        for row in rows:
            row['extras'] = [row['width']] if show_width else []
        title = (f'--- {args.domain}/{args.cohort} regime={name} '
                 f'({len(REGIMES[name])} support regions) macro NRMSE @{args.ratio:.0%}')
        print(render(rows, PROTOCOLS, columns, title))
        payload[name] = rows
        if args.bootstrap:
            strongest = min((row for row in rows if row['method'] in dict(CLASSICAL)),
                            key=lambda row: row['mean'])
            grouped = group_accumulator([frozen_records(args.domain, args.cohort),
                                         args.baseline_records, args.unified_records],
                                        [args.unified_method, strongest['method']],
                                        segments=REGIMES[name])
            for protocol, _ in PROTOCOLS:
                try:
                    prepared = prepare(grouped, protocol, args.ratio)
                    result = bootstrap_delta(prepared, args.unified_method, strongest['method'],
                                             replicates=2000)
                except ValueError as error:
                    print(f'    ({protocol}: {error})')
                    continue
                payload.setdefault('intervals', []).append(dict(regime=name, **result))
                print(f"    {protocol:14s} vs {strongest['method']:10s} "
                      f"delta {result['delta']:+.5f} [{result['low']:+.5f}, {result['high']:+.5f}] "
                      f"P(better)={result['probability_better']:.3f} groups={result['group_count']}")
        print()

    if args.output:
        output = new_run(args.output)
        write_json(output / 'COMPLETED.json', dict(
            domain=args.domain, cohort=args.cohort, ratio=args.ratio, regimes=payload,
            baseline_definition='docs/baseline.md',
            scope='regime re-cut of frozen cohorts; no configuration selection'))
        print(f'written to {output}')


if __name__ == '__main__':
    main()
