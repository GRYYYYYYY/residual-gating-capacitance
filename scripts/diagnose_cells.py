"""Which corrective basis element would have won each cell, and what does the
trained gate actually put its weight on?

This is the diagnostic that explains a losing cell rather than restating it.
For one cohort it reports, per (regime, protocol):

* the pooled NRMSE of every single basis element used *alone* -- the oracle
  reading of the basis, i.e. what a hard selector over the same dictionary would
  have scored;
* the assembled estimate of the trained network;
* the mean gate weight per element, over the queries of that cell.

Read-only: it never writes into a run directory and never touches `pdkcap-v0`.
"""
import argparse
import json
import multiprocessing as mp
import os
import sys
from pathlib import Path

# BLAS reads these at load time, so they must be set before numpy is imported.
# Setting them later (as a pool initializer does) leaves every forked worker
# with a full-size thread pool and the workers thrash each other instead of
# running: measured 40 s of work taking 30 min.
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_name, '1')

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unified.basis import CLASSICAL  # noqa: E402
from unified.episodes import encode, stack  # noqa: E402
from unified.regime import REGIMES  # noqa: E402
from unified.score import load_members  # noqa: E402
from unified.workspace import archive_on_path, os_threads  # noqa: E402

archive_on_path()

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.round2_train import episodes  # noqa: E402
from pdkcap.round3_support import SEGMENTS  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

WORKER = {}
REGIME_OF_SEGMENT = {SEGMENTS.index(name): label
                     for label, members in REGIMES.items() for name in members}


def _init(checkpoints, tables, protocols, ratio):
    os_threads(1)
    import torch
    torch.set_num_threads(1)
    WORKER['members'], WORKER['scales'] = load_members(checkpoints)
    WORKER['tables'] = tables
    WORKER['protocols'] = protocols
    WORKER['ratio'] = ratio


def _run(index):
    import torch
    members, scales = WORKER['members'], WORKER['scales']
    table = WORKER['tables'][index]
    truth = np.asarray(table['labels'], float)
    rows = []
    for _, protocol, ratio, seed, observed, query in episodes([table]):
        if protocol not in WORKER['protocols'] or ratio != WORKER['ratio']:
            continue
        encoded = encode(table, observed, truth[observed], scales)
        batch = stack([encoded])
        target_scales = np.asarray(encoded['scales'], float)
        anchor = encoded['anchor'][:encoded['n']].astype(float)
        elements = {'anchor': anchor}
        for slot, name in enumerate(encoded['basis_names']):
            elements[name] = anchor + np.nan_to_num(encoded['delta'][slot])
        with torch.inference_mode():
            assembled, weights = [], []
            for model in members:
                prediction, info = model(
                    batch['features'], batch['anchor'], batch['gate'], batch['delta'],
                    batch['valid'], padding=batch['padding'], clamp_lower=batch['lower'],
                    clamp_upper=batch['upper'], inside=batch['inside'], return_gate=True)
                assembled.append(prediction[0, :encoded['n']].numpy())
                weights.append(info['weights'][0, :encoded['n']].numpy())
            elements['neural'] = anchor + info['residual'][0, :encoded['n']].numpy()
            elements['neural_clamp'] = anchor + info['clamped'][0, :encoded['n']].numpy()
        rows.append(dict(protocol=protocol, ratio=ratio, mask_seed=seed, query=query,
                         segment=encoded['segment'][query], truth=truth[query],
                         scales=target_scales,
                         elements={k: v[query] for k, v in elements.items()},
                         assembled=np.mean(assembled, axis=0)[query],
                         weights=np.mean(weights, axis=0)[query]))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, nargs='+', required=True)
    parser.add_argument('--protocols', nargs='+', default=['mcar', 'block', 'extrapolation'])
    parser.add_argument('--ratio', type=float, default=.3)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--json', type=Path, default=None, help='also write the numbers here')
    args = parser.parse_args()

    tables = unique_tables(read_tables(args.cohort))
    parts = max(1, min(args.workers, len(tables)))
    with mp.get_context('fork').Pool(parts, initializer=_init,
                                     initargs=(args.checkpoint, tables,
                                               tuple(args.protocols), args.ratio)) as pool:
        rows = [row for result in pool.imap_unordered(_run, range(len(tables)))
                for row in result]

    # Slot 0 of CLASSICAL *is* the anchor, so it must not be listed twice: the
    # gate weight vector has one entry per basis slot, not per display name.
    basis = [*CLASSICAL, 'neural', 'neural_clamp']
    cells, alone, weight = {}, {}, {}
    for row in rows:
        # Every quantity the model produces is in training-normalized units, so
        # the truth is normalized the same way before any error is formed.
        truth = row['truth'] / row['scales'][None, :]
        labels = np.asarray([REGIME_OF_SEGMENT[int(s)] for s in row['segment']])
        for regime in np.unique(labels):
            take = labels == regime
            key = (row['protocol'], str(regime))
            entry = cells.setdefault(key, [0., 0., 0])
            entry[0] += float(((row['assembled'][take] - truth[take]) ** 2).sum())
            entry[1] += float((truth[take] ** 2).sum())
            entry[2] += int(take.sum())
            weight.setdefault(key, []).append(row['weights'][take].mean(axis=0))
            for name, values in row['elements'].items():
                slot = alone.setdefault((row['protocol'], str(regime), name), [0., 0.])
                slot[0] += float(((values[take] - truth[take]) ** 2).sum())
                slot[1] += float((truth[take] ** 2).sum())

    report = {}
    for (protocol, regime), entry in sorted(cells.items()):
        mean_weight = np.mean(weight[(protocol, regime)], axis=0)
        report[f'{protocol}|{regime}'] = dict(
            assembled=float(np.sqrt(entry[0] / entry[1])), n=int(entry[2]),
            alone={name: (float(np.sqrt(alone[(protocol, regime, name)][0]
                                    / alone[(protocol, regime, name)][1]))
                         if (protocol, regime, name) in alone else None)
                   for name in basis},
            weight={name: float(mean_weight[index].mean())
                    for index, name in enumerate(basis)})
    for key, value in report.items():
        print(f'== {key}  (n={value["n"]})')
        print(f'   {"assembled":20s}      {value["assembled"]:9.4f}')
        for name in basis:
            if value['alone'][name] is None:
                continue
            print(f'   {name:20s} alone {value["alone"][name]:9.4f}   weight {value["weight"][name]:6.3f}')
    if args.json is not None:
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
