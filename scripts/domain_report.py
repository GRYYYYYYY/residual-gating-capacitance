"""One domain's confirmation and validation cells: baselines, ours, by regime.

The comparison the paper makes, in the form a screen needs it: for one cohort
and one regime it prints the verified mean-mask macro NRMSE of every applicable
`docs/baseline.md` baseline next to the candidate checkpoints, and marks the
cells where the candidate is not the best baseline-eligible method.
"""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, mask_macro_nrmse, stream_records  # noqa: E402
from unified.regime import regroup  # noqa: E402
from unified.workspace import ARCHIVE  # noqa: E402

PROTOCOLS = (('mcar', 'Random'), ('block', 'Block'), ('extrapolation', 'Extrap.'))
BASELINE = (('cmi1d', 'CMI-1D'), ('cmi2d', 'CMI-2D'), ('cmi4d', 'CMI-4D'),
            ('openrcx_li', 'OpenRCX-LI'), ('pchip', 'PCHIP'), ('idw', 'IDW'), ('gp', 'RBF-GP'))
#: Rank of each dataset's table.  Only the commercial multilinear rule is
#: dimension-restricted: it is shown only at its own rank, because a
#: mismatched call is undefined and would otherwise answer through the shared
#: fallback, flattering the baseline.  The generic interpolators are defined at
#: any rank and are always shown.
RANK = {'public': 1, 'reference': 2, 'to_asap7': 2}
RANK_OF = {'cmi1d': 1, 'cmi2d': 2, 'cmi4d': 4}
CONFIRMATION = {
    'public': ('round3_fixed_public_retrospective_original_v1', 'runs/bl3_public_conf'),
    'reference': ('round3_fixed_reference_confirmation_round3_main_v1', 'runs/bl3_reference_conf'),
    'to_asap7': ('round3_fixed_to_asap7_confirmation_round3_main_v1', 'runs/bl3_to_asap7_conf'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', required=True)
    parser.add_argument('--cohort', choices=('confirmation', 'validation'), default='confirmation')
    parser.add_argument('--ours', type=Path, nargs='+', default=[])
    parser.add_argument('--ours-method', nargs='+', default=[])
    parser.add_argument('--ratio', type=float, default=.3)
    parser.add_argument('--json', type=Path, default=None)
    args = parser.parse_args()
    if len(args.ours) != len(args.ours_method):
        raise ValueError('--ours and --ours-method must line up')

    accumulator = {}
    if args.cohort == 'confirmation':
        frozen, baseline = CONFIRMATION[args.domain]
        add_records(accumulator, ARCHIVE / 'runs' / frozen / 'records.jsonl.gz')
        add_records(accumulator, ROOT / baseline / 'records.jsonl.gz')
    else:
        add_records(accumulator, ROOT / f'runs/frozen_val_records_{args.domain}_v1/records.jsonl.gz')
    for path in args.ours:
        add_records(accumulator, path)
    regimes = regroup(accumulator)

    rank = RANK[args.domain]
    applicable = [(name, label) for name, label in BASELINE
                  if not name.startswith('cmi') or RANK_OF[name] == rank]
    rows = []
    for regime in sorted(regimes):
        grid = {}
        for name, label in [*applicable, *((m, m) for m in args.ours_method)]:
            grid[label] = [mask_macro_nrmse(regimes[regime], name, protocol, args.ratio)
                           for protocol, _ in PROTOCOLS]
        baseline_best = [min((grid[label][index] for _, label in applicable
                              if grid[label][index] is not None), default=None)
                         for index in range(len(PROTOCOLS))]
        head = f"{'method':22s}" + ''.join(f'{name:>10s}' for _, name in PROTOCOLS)
        print(f'--- {args.domain}/{args.cohort} {regime}  (macro NRMSE @{args.ratio:.0%}, '
              f'table rank {rank})')
        print(head)
        for label in [*(label for _, label in applicable), *args.ours_method]:
            cells = []
            for index, value in enumerate(grid[label]):
                if value is None:
                    cells.append('        --')
                else:
                    mark = ' ' if label in args.ours_method and baseline_best[index] is not None \
                        and value > baseline_best[index] else ' '
                    cells.append(f'{value:9.4f}{mark}')
            print(f'{label:22s}' + ''.join(cells))
        ours_best = [min((grid[label][index] for label in args.ours_method
                          if grid[label][index] is not None), default=None)
                     for index in range(len(PROTOCOLS))]
        verdict = []
        for index, _ in enumerate(PROTOCOLS):
            if ours_best[index] is None or baseline_best[index] is None:
                verdict.append('none')
            elif ours_best[index] <= baseline_best[index]:
                verdict.append('win')
            else:
                verdict.append(f'lose ({ours_best[index] / baseline_best[index]:.2f}x)')
        print(f'{"best baseline":22s}' + ''.join(
            '        --' if value is None else f'{value:10.4f}' for value in baseline_best))
        print(f'{"ours":22s}' + ''.join(
            '        --' if value is None else f'{value:10.4f}' for value in ours_best)
              + '   ' + ' '.join(verdict))
        print()
        rows.append(dict(regime=regime, grid=grid, baseline_best=baseline_best,
                         ours_best=ours_best, verdict=verdict))
    if args.json is not None:
        import json
        args.json.write_text(json.dumps(rows, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
