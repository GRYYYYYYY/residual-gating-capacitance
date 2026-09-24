"""Count the cells where a candidate beats the best applicable baseline.

Per cohort and regime, at the reported missingness rate, this compares a
candidate's recorded scores against the strongest of the `docs/baseline.md`
baselines that is defined at that table's rank -- and prints the cells where it
does not win, so the paper's claim and its exceptions come from one place.
"""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, condition_index, mask_macro_nrmse  # noqa: E402
from unified.regime import regroup  # noqa: E402

PROTOCOLS = (('mcar', 'Random'), ('block', 'Block'), ('extrapolation', 'Extrap.'))
COHORTS = (('public', 'bl3_public_conf', ('cmi1d',)),
           ('reference', 'bl3_reference_conf', ('cmi2d',)),
           ('to_asap7', 'bl3_to_asap7_conf', ('cmi2d',)),
           ('to_freepdk15', 'bl3_to_freepdk15_conf', ('cmi2d',)))
BASELINE = ('cmi1d', 'cmi2d', 'cmi4d', 'openrcx_li', 'pchip', 'idw', 'gp')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, action='append', default=[],
                        help='confirmation records for the candidate, one per cohort in order')
    parser.add_argument('--method', action='append', default=[],
                        help='method tag inside the corresponding candidate file')
    parser.add_argument('--label', default='candidate')
    parser.add_argument('--ratio', type=float, default=.3)
    args = parser.parse_args()
    if len(args.candidate) != len(COHORTS) or len(args.method) != len(COHORTS):
        raise ValueError('one candidate record file and method per cohort are required')

    wins, losses, rows = 0, 0, []
    cmi_wins = cmi_losses = 0
    for (domain, baseline_run, applicable), path, method in zip(COHORTS, args.candidate, args.method):
        accumulator = {}
        add_records(accumulator, ROOT / 'runs' / baseline_run / 'records.jsonl.gz')
        add_records(accumulator, path)
        grouped = regroup(accumulator)
        for regime in ('inside', 'outside'):
            index = condition_index(grouped[regime])
            for protocol, label in PROTOCOLS:
                defined = [mask_macro_nrmse(grouped[regime], name, protocol, args.ratio, index=index)
                           for name in BASELINE
                           if not name.startswith('cmi') or name in applicable]
                best = min((value for value in defined if value is not None), default=None)
                commercial = min((mask_macro_nrmse(grouped[regime], name, protocol, args.ratio,
                                                   index=index) for name in applicable), default=None)
                ours = mask_macro_nrmse(grouped[regime], method, protocol, args.ratio, index=index)
                if best is None or ours is None:
                    continue
                ok = ours <= best
                wins += ok
                losses += not ok
                cmi_wins += ours <= commercial
                cmi_losses += ours > commercial
                rows.append(dict(cohort=domain, regime=regime, protocol=label, ours=ours,
                                 baseline=best, commercial=commercial, win=bool(ok)))
                print(f"{'win ' if ok else 'LOSE'} {domain:13s} {regime:8s} {label:7s} "
                      f"ours {ours:7.4f}  best-baseline {best:7.4f}"
                      + ('' if ok else f'  ({ours / best:.2f}x)'))
    print(f'{args.label}: beats the strongest applicable baseline in {wins} of {wins + losses} '
          f'cells, and the applicable commercial multilinear rule in {cmi_wins} of '
          f'{cmi_wins + cmi_losses}')
    return rows


if __name__ == '__main__':
    main()
