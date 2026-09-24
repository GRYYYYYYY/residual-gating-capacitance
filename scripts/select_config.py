"""Select one configuration per domain, on that domain's validation cohort only.

The rule is declared once, before looking at any cohort score, and applied
unchanged:

    score(config) = equal-weight mean of the Random / Block / Extrapolation
                    validation macro NRMSEs at 30% missingness
    select        = the config with the smallest score, provided it also beats
                    the archived SACE-Select policy on the same cohort

Ties and near-ties are reported rather than resolved silently.  Nothing here
touches a confirmation or test cohort.
"""
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, mask_macro_nrmse, stream_records  # noqa: E402
from unified.workspace import new_run, write_json  # noqa: E402

PROTOCOLS = ('mcar', 'block', 'extrapolation')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', required=True)
    parser.add_argument('--config', action='append', required=True,
                        metavar='NAME=runs/<run dir>')
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()

    accumulator = stream_records(ROOT / 'runs' / f'frozen_val_records_{args.domain}_v1' /
                                 'records.jsonl.gz')
    configs = []
    for item in args.config:
        name, path = item.split('=', 1)
        configs.append((name, path))
        add_records(accumulator, ROOT / path / 'records.jsonl.gz')

    rows = []
    for name, path in configs:
        values = [mask_macro_nrmse(accumulator, name, protocol, .3) for protocol in PROTOCOLS]
        if any(value is None for value in values):
            raise ValueError(f'{name}: undefined validation cell')
        rows.append(dict(name=name, path=path, scores=values, mean=sum(values) / len(values)))
    reference = [mask_macro_nrmse(accumulator, 'fixed', protocol, .3) for protocol in PROTOCOLS]
    linear = [mask_macro_nrmse(accumulator, 'linear', protocol, .3) for protocol in PROTOCOLS]

    rows.sort(key=lambda row: row['mean'])
    header = f"{'config':24s}" + ''.join(f'{p:>12s}' for p in PROTOCOLS) + f"{'mean':>12s}"
    print(f'=== {args.domain} validation ({len(configs)} configs)')
    print(header)
    print('-' * len(header))
    print(f"{'SACE-Select':24s}" + ''.join(f'{v:12.4f}' for v in reference)
          + f'{sum(reference) / 3:12.4f}')
    print(f"{'Linear':24s}" + ''.join(f'{v:12.4f}' for v in linear) + f'{sum(linear) / 3:12.4f}')
    for row in rows:
        print(f"{row['name']:24s}" + ''.join(f'{v:12.4f}' for v in row['scores'])
              + f"{row['mean']:12.4f}")
    best = rows[0]
    beats = [best['scores'][index] < reference[index] for index in range(len(PROTOCOLS))]
    print(f"\nselected: {best['name']}  mean={best['mean']:.4f}  "
          f"vs SACE-Select on {sum(beats)}/3 validation protocols "
          f"({'PASS' if all(beats) else 'CHECK'})")
    if args.output:
        output = new_run(args.output)
        write_json(output / 'COMPLETED.json', dict(
            domain=args.domain, rule='smallest equal-weight mean of the three validation protocol macros',
            selected=best['name'], selected_mean=best['mean'], rows=rows,
            sace_select=reference, linear=linear,
            note='validation-only selection; confirmation cohorts not consulted'))
        print(f'written to {output}')


if __name__ == '__main__':
    main()
