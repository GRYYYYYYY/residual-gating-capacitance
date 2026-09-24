"""Score the `docs/baseline.md` interpolation set on a frozen evaluation cohort.

Uses the same episode enumeration, the same mask re-derivation and the same
record schema as :mod:`unified.score`, so the classical baselines and the
unified network are aggregated by one function and compared on one population.
Every classical method shares one floor (the frozen linear/nearest control) for
the queries it cannot answer, and additionally reports, per record, the mean
width of the bracketing cell it had to use and how often that cell was a single
grid step.
"""
import argparse
import gzip
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

from .cmi import METHODS, interpolation_set
from .score import dependency_group, episode_chunks, plan_episodes
from .workspace import (file_hash, input_hashes, new_run, os_threads,
                        source_hashes, write_json)
from .workspace import archive_on_path

archive_on_path()

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.metrics import record  # noqa: E402
from pdkcap.round3_support import SEGMENTS  # noqa: E402
from pdkcap.sampling import mask  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

WORKER = {}


def read_segments(path, count):
    """Frozen per-query support regions, keyed by episode index.

    The frozen fixed evaluator already recorded the region of every scored query
    of every episode.  Reusing it keeps the region labels bit-identical to every
    other table in the study and removes a support description from the hot loop.
    """
    import gzip
    segments = {}
    with gzip.open(path, 'rt') as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            segments[int(row['episode'])] = np.asarray(row['scored_segment'], int)
    if len(segments) != count:
        raise ValueError(f'expected {count} frozen episodes, found {len(segments)}')
    return segments


def _init(plans, tables, segments):
    os_threads(1)
    WORKER['plans'], WORKER['tables'] = plans, tables
    WORKER['segments'] = segments


def _run(chunk):
    tables, plans, segments = WORKER['tables'], WORKER['plans'], WORKER['segments']
    rows = []
    for episode_id in chunk:
        table_index, protocol, ratio, seed = plans[episode_id]
        table = tables[table_index]
        truth = np.asarray(table['labels'], float)
        observed, query = mask(table['coordinates'], protocol, ratio, seed)
        methods, floor, policy = interpolation_set(table, observed, truth[observed], table['coordinates'])
        segment = segments[episode_id]
        rows.append(dict(episode=episode_id, table=table, protocol=protocol, ratio=ratio,
                         mask_seed=seed, query=query, truth=truth, methods=methods, floor=floor,
                         floor_policy=policy, segment=segment))
    return rows


def write_records(path, ordered, names):
    written = 0
    with gzip.open(path, 'wt') as handle:
        for row in ordered:
            truth, query = row['truth'], row['query']
            for name in names:
                prediction, width, adjacent, policy = row['methods'][name]
                for index, region in enumerate(SEGMENTS):
                    requested = query if region == 'all' else query[row['segment'] == index]
                    if not len(requested):
                        continue
                    payload = record(row['table'], truth[requested], prediction[requested],
                                     episode=row['episode'], method=name, training_seed='classical',
                                     protocol=row['protocol'], ratio=row['ratio'],
                                     mask_seed=row['mask_seed'], segment=region,
                                     requested_n=len(query), coverage=len(requested) / len(query),
                                     scored_indices=requested.tolist(),
                                     training_scale=np.asarray(
                                         np.ones(truth.shape[1]), float).tolist(),
                                     dependency_group=dependency_group(row['table']),
                                     policy=policy,
                                     mean_cell_width=float(np.mean(width[requested])),
                                     adjacent_fraction=float(np.mean(adjacent[requested])))
                    handle.write(json.dumps(payload, allow_nan=False) + '\n')
                    written += 1
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--methods', nargs='+', default=list(METHODS))
    parser.add_argument('--segments-from', type=Path, required=True,
                        help='frozen episodes.jsonl.gz holding the per-query support regions')
    args = parser.parse_args()
    if not args.cohort.exists():
        raise FileNotFoundError(args.cohort)
    unknown = [name for name in args.methods if name not in METHODS]
    if unknown:
        raise ValueError(f'unknown baseline methods: {unknown}')

    output = new_run(args.output)
    tables = unique_tables(read_tables(args.cohort))
    plans = plan_episodes(tables)
    segments = read_segments(args.segments_from, len(plans))
    partitions = sorted({table['partition'] for table in tables})
    if len(partitions) != 1:
        raise ValueError(f'cohort mixes partitions: {partitions}')
    write_json(output / 'FROZEN.json', dict(
        cohort=str(args.cohort), cohort_sha256=file_hash(args.cohort),
        segments_from=str(args.segments_from), segments_sha256=file_hash(args.segments_from),
        methods=list(args.methods),
        tables=len(tables), episodes=len(plans), workers=args.workers, partitions=partitions,
        sources=source_hashes(), inputs=input_hashes(),
        baseline_definition='docs/baseline.md',
        label_access='masked support only for prediction; query truth used for scoring only'))

    started = time.perf_counter()
    parts = max(1, min(args.workers, len(plans)))
    work = [chunk for chunk in episode_chunks(len(plans), parts) if chunk]
    results = {}
    with mp.get_context('fork').Pool(parts, initializer=_init,
                                     initargs=(plans, tables, segments)) as pool:
        for rows in pool.imap_unordered(_run, work):
            for row in rows:
                results[row['episode']] = row
    if len(results) != len(plans):
        raise ValueError(f'scored {len(results)} of {len(plans)} episodes')
    written = write_records(output / 'records.jsonl.gz',
                            [results[index] for index in range(len(plans))], args.methods)
    write_json(output / 'COMPLETED.json', dict(
        status='classical baselines scored; aggregation pending', methods=list(args.methods),
        episodes=len(plans), records=written, tables=len(tables),
        records_sha256=file_hash(output / 'records.jsonl.gz'),
        elapsed_seconds=time.perf_counter() - started))


if __name__ == '__main__':
    main()
