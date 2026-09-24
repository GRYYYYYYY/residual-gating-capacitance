"""Per-query latency of every method, on one host, one thread, interleaved.

The interpolation step is what `docs/baseline.md` compares, so the measured
quantity is the wall time to answer one episode's query set from an already
loaded support, including everything the method needs to get there -- support
reduction for the classical rules, and support reduction plus the token stream
and one trunk forward for the unified network.  Order is shuffled per round so
slow and fast methods see the same cache and frequency state, the first round is
discarded, and the reported statistics are the median and p95 over the rest.
"""
import argparse
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

# BLAS reads these at load time: setting them afterwards (as os_threads does,
# for torch) leaves every BLAS call running on a full-size thread pool, which on
# matrices this small costs far more than the arithmetic.  Pinning one thread
# before numpy is imported is what makes the measurement a single-thread one.
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_name, '1')

import numpy as np  # noqa: E402

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.cmi import METHODS, multilinear, separation_curve  # noqa: E402
from unified.episodes import encode, stack  # noqa: E402
from unified.score import load_members  # noqa: E402
from unified.workspace import ARCHIVE, new_run, os_threads, write_json  # noqa: E402

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.sampling import mask  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

DOMAINS = {
    'public': dict(tables=ARCHIVE / 'runs/public_inventory_v1/tables.jsonl',
                   partition='test',
                   checkpoints=[f'runs/g16_s{seed}/checkpoint.pt' for seed in range(3)]),
    'reference': dict(tables=ARCHIVE / 'runs/round3_reference_dataset_v1/tables.jsonl',
                      partition='confirmation',
                      checkpoints=[f'runs/v10_reference_all_s{seed}/checkpoint.pt' for seed in range(3)]),
}
"""Timing measures the deployed three-seed ensemble, not a single member."""



def sample_episodes(tables, partition, count, ratio=0.5):
    """One episode per (process, family) cell, largest table first, deterministic."""
    cells = {}
    for table in tables:
        if table['partition'] != partition:
            continue
        key = (table['process_id'], table['family'])
        if key not in cells or len(table['coordinates']) > len(cells[key]['coordinates']):
            cells[key] = table
    chosen = [cells[key] for key in sorted(cells)][:count]
    episodes = []
    for table in chosen:
        truth = np.asarray(table['labels'], float)
        observed, query = mask(table['coordinates'], 'mcar', ratio, 29)
        episodes.append(dict(table=table, observed=observed, query=query, truth=truth,
                             values=truth[observed]))
    return episodes


def prepare(episode):
    """Support reduction and the shared fallback, outside every timed region.

    Each method is then timed on everything it still has to do to answer the
    query set: its own rule, or the token stream and trunk forward for the
    unified network.  Charging every classical rule for the whole expert set --
    which is what the frozen evaluator computes -- would hide the differences
    this table is about.
    """
    from pdkcap.interpolation import predict, reduce_coordinates
    table = episode['table']
    x = np.asarray(table['coordinates'], float)
    observed = np.asarray(episode['observed'], int)
    values = np.asarray(episode['values'], float)
    reduced, queries, axes = reduce_coordinates(x[observed], x)
    floor, _ = predict(x[observed], values, x, 'linear')
    separation = axes.index(1) if 1 in axes else 0
    other = next((axis for axis in range(len(axes)) if axis != separation), separation)
    return dict(reduced=reduced, queries=queries, dims=len(axes), floor=floor,
                separation=separation, other=other)


def time_classical(name, episodes, shared):
    samples = []
    for episode, context in zip(episodes, shared):
        started = time.perf_counter()
        if name in ('cmi1d', 'cmi2d', 'cmi4d'):
            multilinear(context['reduced'], episode['values'], context['queries'],
                        {'cmi1d': 1, 'cmi2d': 2, 'cmi4d': 4}[name], context['floor'])
        elif name in ('openrcx_li', 'pchip'):
            separation_curve(context['reduced'], episode['values'], context['queries'],
                             context['dims'], context['floor'], context['separation'],
                             context['other'], 'pchip' if name == 'pchip' else 'linear')
        else:
            from pdkcap.interpolation import predict
            table = episode['table']
            predict(np.asarray(table['coordinates'], float)[episode['observed']],
                    episode['values'], np.asarray(table['coordinates'], float), name)
        samples.append(time.perf_counter() - started)
    return samples


def summarize(rounds, query_counts):
    """One episode time per round; per-query statistics over every episode-round."""
    matrix = np.asarray(rounds, float)
    counts = np.asarray(query_counts, float)[None, :]
    if matrix.shape[1] != len(counts[0]):
        raise ValueError('episode count does not match the recorded timing width')
    per_episode = matrix.reshape(-1)
    per_query = (matrix / counts).reshape(-1)
    return dict(median_seconds=float(np.median(per_episode)),
                p95_seconds=float(np.quantile(per_episode, .95)),
                mean_seconds=float(per_episode.mean()),
                median_per_query_ms=float(np.median(per_query)) * 1e3,
                p95_per_query_ms=float(np.quantile(per_query, .95)) * 1e3,
                rounds=int(matrix.shape[0]), episode_rounds=int(per_episode.size))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', choices=sorted(DOMAINS), default='public')
    parser.add_argument('--episodes', type=int, default=8)
    parser.add_argument('--rounds', type=int, default=30)
    parser.add_argument('--ratio', type=float, default=.5)
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()
    os_threads(1)
    import torch
    torch.set_num_threads(1)

    spec = DOMAINS[args.domain]
    tables = unique_tables(read_tables(spec['tables']))
    episodes = sample_episodes(tables, spec['partition'], args.episodes, args.ratio)
    counts = [len(episode['query']) for episode in episodes]
    shared = [prepare(episode) for episode in episodes]
    rng = random.Random(20260922)
    names = [*METHODS, 'unified']
    members, scales = load_members([str(ROOT / path) for path in spec['checkpoints']])

    def run_unified():
        import torch
        samples = []
        for episode in episodes:
            started = time.perf_counter()
            encoded = encode(episode['table'], episode['observed'], episode['values'], scales)
            batch = stack([encoded])
            with torch.inference_mode():
                for model in members:
                    model(batch['features'], batch['anchor'], batch['gate'], batch['delta'],
                          batch['valid'], padding=batch['padding'], clamp_lower=batch['lower'],
                          clamp_upper=batch['upper'], inside=batch['inside'])
            samples.append(time.perf_counter() - started)
        return samples

    results = {}
    for round_index in range(args.rounds + 1):
        order = names[:]
        rng.shuffle(order)
        for name in order:
            samples = run_unified() if name == 'unified' else time_classical(name, episodes, shared)
            if round_index == 0:
                continue                          # discarded warm-up round
            results.setdefault(name, []).append(samples)
    report = {name: summarize(values, counts) for name, values in results.items()}
    order = sorted(report, key=lambda name: report[name]['median_seconds'])
    print(f'domain={args.domain}  episodes={len(episodes)}  queries/episode={counts}  '
          f'rounds={args.rounds} (first discarded)  threads=1')
    print(f"{'method':12s}{'median ms/episode':>20s}{'p95 ms/episode':>16s}{'ms/query':>12s}")
    for name in order:
        row = report[name]
        print(f'{name:12s}{row["median_seconds"] * 1e3:20.3f}{row["p95_seconds"] * 1e3:16.3f}'
              f'{row["median_per_query_ms"]:12.3f}')
    if args.output:
        output = new_run(args.output)
        write_json(output / 'COMPLETED.json', dict(
            domain=args.domain, episodes=len(episodes), queries_per_episode=counts,
            rounds=args.rounds, discarded_rounds=1, torch_threads=1,
            checkpoints=spec['checkpoints'], members=len(members), report=report,
            note='one host, one thread, interleaved order; shared machine, not a dedicated benchmark'))
        print(f'\nwritten to {output}')
    else:
        print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
