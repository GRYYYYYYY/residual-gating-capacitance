"""Per-platform latency, same measurement as ``benchmark_interpolation.py``.

``benchmark_interpolation`` reports one aggregate over its episode set, and on
the public rules that set is the first eight (process, family) cells in sorted
order -- the two alphabetically first processes.  This run keeps the identical
protocol (one host, one thread, interleaved order, first round discarded, same
episodes, same checkpoints) but keeps the per-episode samples, so the same
measurement can be read platform by platform.

The unit is one table's query set: the benchmark answers one episode at a time,
so a batch is one table.  ``points/s`` therefore counts the scored queries of
that episode, which is what the timed region produces.
"""
import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Imported before numpy: this module pins the BLAS thread count at import time,
# and a thread count set after numpy is loaded leaves every BLAS call on a
# full-size pool, which on matrices this small costs more than the arithmetic.
import benchmark_interpolation as base  # noqa: E402
import numpy as np  # noqa: E402
from unified.workspace import os_threads, new_run, write_json  # noqa: E402
from pdkcap.common import read_tables  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

ROOT = base.ROOT


def summarize(indices, rounds, counts):
    """Summaries over the episode-rounds whose index is in ``indices``."""
    columns = [i for i in indices]
    block = np.asarray([[row[i] for i in columns] for row in rounds], float)
    counts_local = np.asarray([counts[i] for i in columns], float)[None, :]
    per_episode = block.reshape(-1)
    per_query = (block / counts_local).reshape(-1)
    return dict(episodes=len(columns),
                episode_rounds=int(per_episode.size),
                queries_per_episode=[counts[i] for i in columns],
                median_seconds=float(np.median(per_episode)),
                p95_seconds=float(np.quantile(per_episode, .95)),
                median_per_query_ms=float(np.median(per_query)) * 1e3,
                p95_per_query_ms=float(np.quantile(per_query, .95)) * 1e3,
                mean_queries=float(counts_local.mean()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', choices=sorted(base.DOMAINS), default='public')
    parser.add_argument('--rounds', type=int, default=50)
    parser.add_argument('--ratio', type=float, default=.5)
    parser.add_argument('--output', type=str, required=True)
    args = parser.parse_args()

    os_threads(1)
    import torch
    torch.set_num_threads(1)

    spec = base.DOMAINS[args.domain]
    tables = unique_tables(read_tables(spec['tables']))
    # Every (process, family) cell, not the first `count` of them: a per-platform
    # table needs every platform represented.
    cells = {}
    for table in tables:
        if table['partition'] != spec['partition']:
            continue
        key = (table['process_id'], table['family'])
        if key not in cells or len(table['coordinates']) > len(cells[key]['coordinates']):
            cells[key] = table
    chosen = [cells[key] for key in sorted(cells)]
    episodes = []
    for table in chosen:
        truth = np.asarray(table['labels'], float)
        observed, query = base.mask(table['coordinates'], 'mcar', args.ratio, 29)
        episodes.append(dict(table=table, observed=observed, query=query, truth=truth,
                             values=truth[observed]))
    counts = [len(episode['query']) for episode in episodes]
    shared = [base.prepare(episode) for episode in episodes]
    rng = random.Random(20260922)
    names = [*base.METHODS, 'unified']
    members, scales = base.load_members([str(ROOT / path) for path in spec['checkpoints']])

    def run_unified():
        import torch
        samples = []
        for episode in episodes:
            started = time.perf_counter()
            encoded = base.encode(episode['table'], episode['observed'], episode['values'], scales)
            batch = base.stack([encoded])
            with torch.inference_mode():
                for model in members:
                    model(batch['features'], batch['anchor'], batch['gate'], batch['delta'],
                          batch['valid'], padding=batch['padding'], clamp_lower=batch['lower'],
                          clamp_upper=batch['upper'], inside=batch['inside'])
            samples.append(time.perf_counter() - started)
        return samples

    results = defaultdict(list)
    for round_index in range(args.rounds + 1):
        order = names[:]
        rng.shuffle(order)
        for name in order:
            samples = run_unified() if name == 'unified' else base.time_classical(name, episodes, shared)
            if round_index == 0:
                continue
            results[name].append(samples)

    by_platform = defaultdict(list)
    for index, table in enumerate(chosen):
        by_platform[table['process_id']].append(index)
    report = {platform: {name: summarize(indices, results[name], counts)
                         for name in names}
              for platform, indices in sorted(by_platform.items())}
    body = dict(domain=args.domain, ratio=args.ratio, rounds=args.rounds, discarded_rounds=1,
                torch_threads=1, members=len(members), checkpoints=spec['checkpoints'],
                episodes=[dict(process=table['process_id'], family=table['family'],
                               table_id=table['table_id'], queries=counts[i])
                          for i, table in enumerate(chosen)],
                report=report,
                note='one host, one thread, interleaved order; shared machine, not a dedicated '
                     'benchmark. A batch is one table query set. Ratios are read within a '
                     'platform, not across platforms measured in separate calls.')
    output = new_run(args.output)
    write_json(output / 'COMPLETED.json', body)
    print(json.dumps({p: {n: round(r['median_per_query_ms'], 3) for n, r in methods.items()}
                      for p, methods in report.items()}, indent=1))
    print(f'\nwritten to {output}')


if __name__ == '__main__':
    main()
