"""Per-cell macro NRMSE for one or more record files.

A configuration screen, not a results table: it prints the verified mean-mask
macro NRMSE of each named method in every (regime, protocol) cell so candidate
checkpoints can be compared to each other and to the incumbent on the
validation cohort, which is the only cohort a configuration decision may read.
"""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, mask_macro_nrmse, stream_records  # noqa: E402
from unified.regime import regroup  # noqa: E402

PROTOCOLS = (('mcar', 'Random'), ('block', 'Block'), ('extrapolation', 'Extrap.'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--records', type=Path, nargs='+', required=True)
    parser.add_argument('--method', nargs='+', required=True)
    parser.add_argument('--label', nargs='+', default=None)
    parser.add_argument('--ratio', type=float, default=.3)
    parser.add_argument('--json', type=Path, default=None)
    args = parser.parse_args()
    # The record files are pooled into one accumulator first, so several
    # methods may be reported from the same file.
    labels = args.label or args.method
    if len(labels) != len(args.method):
        raise ValueError('method and label must line up')

    accumulator = {}
    for path in args.records:
        add_records(accumulator, path)
    regimes = regroup(accumulator)

    values = {}
    head = f"{'method':24s}" + ''.join(f'{name:>10s}' for _, name in PROTOCOLS) + f"{'mean':>10s}"
    for regime in sorted(regimes):
        print(f'--- {regime}')
        print(head)
        for label, method in zip(labels, args.method):
            cells = [mask_macro_nrmse(regimes[regime], method, protocol, args.ratio)
                     for protocol, _ in PROTOCOLS]
            present = [value for value in cells if value is not None]
            mean = sum(present) / len(present) if present else None
            values[f'{regime}|{label}'] = dict(
                cells={name: value for (_, name), value in zip(PROTOCOLS, cells)}, mean=mean)
            print(f'{label:24s}' + ''.join('        --' if value is None else f'{value:10.4f}'
                                           for value in cells)
                  + ('        --' if mean is None else f'{mean:10.4f}'))
        print()
    if args.json is not None:
        import json
        args.json.write_text(json.dumps(values, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
