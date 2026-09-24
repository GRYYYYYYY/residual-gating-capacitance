"""Per-basis-element and per-gate diagnostics on a bounded episode sample.

Answers three questions without touching the frozen runs: how good each
corrective basis element is on its own, what the trained gate actually puts its
weight on, and where the assembled estimate loses.  Read-only: it never writes
into an existing run directory.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unified.episodes import encode, stack  # noqa: E402
from unified.score import load_members  # noqa: E402
from unified.workspace import SEGMENTS, archive_on_path  # noqa: E402

archive_on_path()

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.round2_train import episodes  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, nargs='+', required=True)
    parser.add_argument('--tables', type=int, default=40)
    parser.add_argument('--protocol', default='mcar')
    parser.add_argument('--ratio', type=float, default=.3)
    args = parser.parse_args()
    torch.set_num_threads(4)

    tables = unique_tables(read_tables(args.data))[:args.tables]
    members, scales = load_members(args.checkpoint)
    names = [m.state_dict() is not None for m in members]
    basis = list(json.load(open('configs/basis_names.json')) if Path('configs/basis_names.json').exists()
                 else ())
    torch.set_grad_enabled(False)
    totals = {}
    weight_sum = {}
    for table in tables:
        truth = np.asarray(table['labels'], float)
        for _, protocol, ratio, seed, observed, query in episodes([table]):
            if protocol != args.protocol or ratio != args.ratio:
                continue
            encoded = encode(table, observed, truth[observed], scales)
            batch = stack([encoded])
            predictions = []
            for model in members:
                prediction, info = model(batch['features'], batch['anchor'], batch['gate'], batch['delta'],
                                         batch['valid'], padding=batch['padding'], clamp_lower=batch['lower'],
                                         clamp_upper=batch['upper'], inside=batch['inside'], return_gate=True)
                predictions.append(prediction)
                weights = info['weights'][0, :encoded['n']].numpy()
            target_scales = np.asarray(encoded['scales'], float)
            assembled = np.mean([p[0, :encoded['n']].numpy() for p in predictions], axis=0) * target_scales
            segment = encoded['segment'][query]
            truth_query = truth[query]
            if not basis:
                basis = [*encoded['basis_names'], 'neural', 'neural_clamp']
            elements = {}
            anchor = encoded['anchor'][:encoded['n']]
            elements['anchor'] = anchor
            for index, name in enumerate(encoded['basis_names']):
                elements[name] = anchor + np.nan_to_num(encoded['delta'][index])
            residual = info['residual'][0, :encoded['n']].numpy()
            elements['neural'] = anchor + residual
            elements['neural_clamp'] = anchor + info['clamped'][0, :encoded['n']].numpy()
            for name, values in elements.items():
                prediction = values[query] * target_scales
                error = ((prediction - truth_query) / target_scales) ** 2
                for index, label in enumerate(SEGMENTS):
                    take = segment == index
                    if not take.any():
                        continue
                    key = (name, label)
                    entry = totals.setdefault(key, [0., 0., 0])
                    entry[0] += float(error[take].sum())
                    entry[1] += float((truth_query[take] ** 2).sum())
                    entry[2] += float(take.sum())
                key = ('gate', 'all')
                entry = totals.setdefault(key, [0., 0., 0])
                assembled_error = ((assembled[query] - truth_query) / target_scales) ** 2
                entry[0] += float(assembled_error.sum())
                entry[1] += float((truth_query ** 2).sum())
                entry[2] += float(len(query))
                for index, label in enumerate(SEGMENTS):
                    take = segment == index
                    if not take.any():
                        continue
                    key = ('gate', label)
                    entry = totals.setdefault(key, [0., 0., 0])
                    entry[0] += float(assembled_error[take].sum())
                    entry[1] += float((truth_query[take] ** 2).sum())
                    entry[2] += float(take.sum())
            for index, label in enumerate(SEGMENTS):
                take = segment == index
                if not take.any():
                    continue
                key = ('__weight__', label)
                entry = weight_sum.setdefault(key, np.zeros((weights.shape[1], weights.shape[2])))
                entry += weights[query][take].sum(axis=0)
    print('basis order:', basis)
    print(f"{'element':16s}" + ''.join(f'{s[:12]:>14s}' for s in SEGMENTS) + f"{'all':>14s}")
    for name in ['anchor', *basis]:
        cells = []
        for label in [*SEGMENTS]:
            entry = totals.get((name, label))
            cells.append(np.sqrt(entry[0] / entry[1]) if entry and entry[1] > 0 else None)
        entry = None
        for label in SEGMENTS:
            row = totals.get((name, label))
            if row and row[1] > 0:
                entry = [0., 0., 0.] if entry is None else entry
                entry = [entry[0] + row[0], entry[1] + row[1], entry[2] + row[2]]
        cells.append(np.sqrt(entry[0] / entry[1]) if entry and entry[1] > 0 else None)
        print(f'{name:16s}' + ''.join(f'{c:14.4f}' if c is not None else '            --' for c in cells))
    print(f"{'gate (assembled)':16s}" + ''.join(
        f"{np.sqrt(totals[('gate', label)][0] / totals[('gate', label)][1]):14.4f}"
        if ('gate', label) in totals and totals[('gate', label)][1] > 0 else '            --'
        for label in [*SEGMENTS, 'all']))
    print()
    print('mean gate weight per support region and target component')
    print(f"{'basis':16s}" + ''.join(f'{s[:12]:>14s}' for s in SEGMENTS))
    for index, name in enumerate(basis):
        for component in range(next(iter(weight_sum.values())).shape[1] if weight_sum else 0):
            cells = []
            for label in SEGMENTS:
                entry = weight_sum.get(('__weight__', label))
                cells.append(entry[index, component] / entry[:, component].sum()
                             if entry is not None and entry[:, component].sum() > 0 else None)
            print(f'{name + f"[k{component}]":16s}'
                  + ''.join(f'{c:14.4f}' if c is not None else '            --' for c in cells))


if __name__ == '__main__':
    main()
