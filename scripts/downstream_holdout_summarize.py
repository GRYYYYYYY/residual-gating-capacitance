"""Turn the re-extraction results into the two requested downstream tables.

Reads ``runs/downstream_holdout_v1/comparisons/`` (this audit) and, for the
classical baseline, the upstream audit's already-recorded ``linear`` variants.
The two audits use the same mask recipe -- the mask depends only on the table id,
the protocol, the ratio and the seed -- so the upstream linear rows are the same
population as ours and are reused rather than recomputed.

Timing differences are relative to golden extraction on a fixed routed layout,
in the units the platform's Liberty files declare, and are not timing-closure
improvements.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = Path(__import__('os').environ.get('RG_UPSTREAM_ROOT', ROOT / 'upstream')).resolve()
FLOW = UPSTREAM / 'tools/OpenROAD-flow-scripts/flow'

PLATFORMS = ('asap7', 'gf180', 'ihp-sg13g2', 'sky130hs')
DESIGNS = ('aes', 'ibex')
RATIOS = (30, 50)
SEEDS = (0, 1, 2)
#: The upstream audit's method name for the classical multilinear completion.
UPSTREAM_LINEAR = 'linear'
OUR_METHODS = ('ours', 'anchor')
LABEL = {'ours': 'Residual gating (ours)', 'anchor': 'Anchor (ours)',
         UPSTREAM_LINEAR: 'Linear'}


def time_scale_ns(log):
    """Liberty time unit of every library read by a report log, in ns.

    Copied from the upstream summariser so both audits convert identically.
    """
    units = set()
    for line in log.read_text().splitlines():
        if not line.startswith('read_liberty '):
            continue
        path = Path(line.split()[-1])
        if not path.is_absolute():
            path = FLOW / path
        import gzip
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as handle:
            header = handle.read(131072)
        match = re.search(r'time_unit\s*:\s*"?([0-9.eE+-]+)\s*(s|ms|us|ns|ps|fs)"?\s*;', header)
        if not match:
            raise ValueError(f'missing Liberty time unit: {path}')
        units.add(float(match[1]) * dict(s=1e9, ms=1e6, us=1e3, ns=1,
                                         ps=1e-3, fs=1e-6)[match[2]])
    if len(units) != 1:
        raise ValueError(f'nonuniform or missing Liberty time units: {log}')
    return units.pop()


def load_variant(root, name, factor, golden_ws, golden_tns):
    path = root / f'{name}.json'
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    ws = value['timing_metrics']['finish__timing__setup__ws'] * factor
    tns = value['timing_metrics']['finish__timing__setup__tns'] * factor
    return dict(
        capacitance_nrmse=value['comparison']['metrics']['capacitance']['nrmse'],
        capacitance_spearman=value['comparison']['metrics']['capacitance']['spearman'],
        worst_slack_ns=ws, tns_ns=tns,
        abs_ws=abs(ws - golden_ws), abs_tns=abs(tns - golden_tns),
        extraction_seconds=value['extraction_seconds'],
        common_nets=value['comparison']['common_nets'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rules-run', default='downstream_holdout_v1')
    parser.add_argument('--ours', default='downstream_holdout_v1')
    parser.add_argument('--upstream', default='downstream')
    args = parser.parse_args()

    ours_root = ROOT / 'runs' / args.ours / 'comparisons'
    upstream_root = UPSTREAM / 'runs' / args.upstream / 'comparisons'
    output = ROOT / 'runs' / args.rules_run
    observations = []
    for platform in PLATFORMS:
        for design in DESIGNS:
            mine = ours_root / platform / design
            theirs = upstream_root / platform / design
            golden = json.loads((mine / 'golden.json').read_text())
            factor = time_scale_ns(mine / 'golden.log')
            golden_ws = golden['timing_metrics']['finish__timing__setup__ws'] * factor
            golden_tns = golden['timing_metrics']['finish__timing__setup__tns'] * factor
            for ratio in RATIOS:
                for seed in SEEDS:
                    for method in OUR_METHODS:
                        row = load_variant(mine, f'{method}_block{ratio}_seed{seed}',
                                           factor, golden_ws, golden_tns)
                        if row is None:
                            raise ValueError(f'missing {method} {platform}/{design} '
                                             f'block{ratio} seed{seed}')
                        observations.append(dict(platform=platform, design=design,
                                                 method=method, ratio=ratio / 100,
                                                 seed=seed, source='this audit', **row))
                    # The classical baseline is the same mask population and was
                    # recorded by the upstream audit; reuse rather than recompute.
                    row = None
                    path = theirs / f'{UPSTREAM_LINEAR}_block{ratio}_seed{seed}.json'
                    if path.exists():
                        value = json.loads(path.read_text())
                        ws = value['timing_metrics']['finish__timing__setup__ws'] * factor
                        tns = value['timing_metrics']['finish__timing__setup__tns'] * factor
                        row = dict(
                            capacitance_nrmse=value['comparison']['metrics']['capacitance']['nrmse'],
                            capacitance_spearman=value['comparison']['metrics']['capacitance']['spearman'],
                            worst_slack_ns=ws, tns_ns=tns,
                            abs_ws=abs(ws - golden_ws), abs_tns=abs(tns - golden_tns),
                            extraction_seconds=value['extraction_seconds'],
                            common_nets=value['comparison']['common_nets'])
                    if row is None:
                        raise ValueError(f'missing upstream linear {platform}/{design} '
                                         f'block{ratio} seed{seed}')
                    observations.append(dict(platform=platform, design=design,
                                             method=UPSTREAM_LINEAR,
                                             ratio=ratio / 100, seed=seed,
                                             source='upstream audit', **row))

    # Per (platform, design, method, mask): seed mean of NRMSE, and the worst
    # absolute timing deviation over the six exports, as in the upstream format.
    cells = []
    for platform in PLATFORMS:
        for design in DESIGNS:
            for method in (*OUR_METHODS, UPSTREAM_LINEAR):
                for ratio in RATIOS:
                    selected = [o for o in observations
                                if (o['platform'], o['design'], o['method'], o['ratio'])
                                == (platform, design, method, ratio / 100)]
                    if not selected:
                        continue
                    nrmse = [o['capacitance_nrmse'] for o in selected]
                    mean = sum(nrmse) / len(nrmse)
                    std = math.sqrt(sum((x - mean) ** 2 for x in nrmse)
                                    / max(1, len(nrmse) - 1))
                    cells.append(dict(
                        platform=platform, design=design, method=method,
                        method_label=LABEL[method], ratio=ratio / 100, seeds=len(selected),
                        capacitance_nrmse_mean=mean, capacitance_nrmse_std=std,
                        max_abs_ws_ns=max(o['abs_ws'] for o in selected),
                        max_abs_tns_ns=max(o['abs_tns'] for o in selected),
                        median_abs_ws_ns=sorted(o['abs_ws'] for o in selected)[len(selected) // 2],
                        extraction_seconds_min=min(o['extraction_seconds'] for o in selected),
                        extraction_seconds_max=max(o['extraction_seconds'] for o in selected)))

    result = dict(
        scope='block masks on held-out rule tables only, on fixed golden routed layouts',
        masks='the same mask recipe as the upstream audit; the upstream linear rows are '
              'the same mask population and are reused, not recomputed',
        caveat='timing columns are absolute deviations from golden extraction, not '
               'timing-closure improvements; no physical guarantee is implied',
        cells=cells, observations=observations)
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'wrote {output / "summary.json"}: {len(cells)} cells, '
          f'{len(observations)} observations')
    for cell in cells:
        print(f"  {cell['platform']:11s} {cell['design']:5s} "
              f"{cell['method_label']:24s} {cell['ratio']:.0%}  "
              f"nrmse={cell['capacitance_nrmse_mean']:.4f}  "
              f"|dWS|={cell['max_abs_ws_ns']:.4g}  |dTNS|={cell['max_abs_tns_ns']:.4g}")


if __name__ == '__main__':
    main()
