"""Score every single element of the corrective dictionary on one cohort.

Emits one record set per dictionary element (``el_<name>``) plus a per-query
``oracle`` that takes, for each query, the applicable element closest to the
truth.  The oracle is not a method -- it reads the label -- but it bounds what
any selector over this dictionary could reach, so the gap between a trained gate
and the oracle is the part of the error that a better gate could still remove,
and the gap between the oracle and the best baseline is the part no gate over
this dictionary can remove.

Read-only with respect to `pdkcap-v0`; writes one new run directory.
"""
import argparse
import gzip
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.basis import CLASSICAL  # noqa: E402
from unified.episodes import encode  # noqa: E402
from unified.score import dependency_group, plan_episodes  # noqa: E402
from unified.workspace import (archive_on_path, file_hash, input_hashes, new_run,  # noqa: E402
                               os_threads, source_hashes, write_json)

archive_on_path()

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.metrics import record  # noqa: E402
from pdkcap.round3_support import SEGMENTS  # noqa: E402
from pdkcap.sampling import mask  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

WORKER = {}


def _init(plans, tables, scales):
    os_threads(1)
    WORKER['plans'], WORKER['tables'], WORKER['scales'] = plans, tables, scales


def _run(chunk):
    tables, plans, scales = WORKER['tables'], WORKER['plans'], WORKER['scales']
    rows = []
    for episode_id in chunk:
        table_index, protocol, ratio, seed = plans[episode_id]
        table = tables[table_index]
        truth = np.asarray(table['labels'], float)
        observed, query = mask(table['coordinates'], protocol, ratio, seed)
        encoded = encode(table, observed, truth[observed], scales)
        target_scales = np.asarray(encoded['scales'], float)
        anchor = encoded['anchor'][:encoded['n']].astype(float)
        predictions = {'anchor': anchor}
        applicable = {'anchor': np.ones(len(query), bool)}
        for slot, name in enumerate(encoded['basis_names']):
            predictions[name] = anchor + np.nan_to_num(encoded['delta'][slot])
            applicable[name] = np.asarray(encoded['valid'][slot])[query]
        error = {name: np.abs(values - truth / target_scales) for name, values in predictions.items()}
        stacked = np.stack([error[name] for name in predictions], axis=0)     # [E, N, K]
        best = np.argmin(stacked.sum(axis=2), axis=0)                         # [N]
        oracle = np.stack([predictions[name] for name in predictions], axis=0)
        predictions['oracle'] = np.take_along_axis(
            oracle, best[None, :, None].repeat(oracle.shape[2], axis=2), axis=0)[0]
        applicable['oracle'] = np.ones(len(query), bool)
        rows.append(dict(episode=episode_id, table=table, protocol=protocol, ratio=ratio,
                         mask_seed=seed, observed=observed, query=query,
                         segment=encoded['segment'], truth=truth, predictions=predictions,
                         applicable=applicable, training_scale=target_scales))
    return rows


def write_records(path, ordered):
    """One record set per element, restricted to the queries where it applies.

    An element that is undefined at a query is not given a fabricated value
    there: its records cover only its own domain, so the score of a rule like
    the shape-preserving cubic on a two-dimensional table is that rule's score
    where it is defined rather than the shared floor's score where it is not.
    The per-query oracle is scored on every query, since it is defined wherever
    at least one element is.
    """
    written = 0
    with gzip.open(path, 'wt') as handle:
        for row in ordered:
            truth, segment, query = row['truth'], row['segment'], row['query']
            for name, values in row['predictions'].items():
                # ``applicable`` is already aligned with ``query``, not with the
                # full node set.
                scored = query[row['applicable'][name]]
                if not len(scored):
                    continue
                scaled = values * row['training_scale'][None, :]
                regions = [('all', scored)] + [(region, scored[segment[scored] == index])
                                               for index, region in enumerate(SEGMENTS)]
                for region, requested in regions:
                    if not len(requested):
                        continue
                    handle.write(json.dumps(record(
                        row['table'], truth[requested], scaled[requested],
                        episode=row['episode'], method=f'el_{name}', training_seed='ensemble',
                        protocol=row['protocol'], ratio=row['ratio'], mask_seed=row['mask_seed'],
                        segment=region, requested_n=len(requested), coverage=1.0,
                        scored_indices=requested.tolist(),
                        training_scale=np.asarray(row['training_scale'], float).tolist(),
                        dependency_group=dependency_group(row['table'])), allow_nan=False) + '\n')
                    written += 1
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--scales-from', type=Path, required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        import os
        os.environ.setdefault(name, '1')

    import torch
    output = new_run(args.output)
    tables = unique_tables(read_tables(args.cohort))
    plans = plan_episodes(tables)
    scales = torch.load(args.scales_from, map_location='cpu', weights_only=True)['scales']
    write_json(output / 'FROZEN.json', dict(
        cohort=str(args.cohort), cohort_sha256=file_hash(args.cohort),
        scales_from=str(args.scales_from), method='basis_elements', tables=len(tables),
        episodes=len(plans), workers=args.workers, sources=source_hashes(), inputs=input_hashes(),
        elements=[*CLASSICAL, 'oracle'],
        label_access='masked support only for prediction; the oracle reads the query label'))
    started = time.perf_counter()
    parts = max(1, min(args.workers, len(plans)))
    size = (len(plans) + parts - 1) // parts
    work = [list(range(start, min(start + size, len(plans)))) for start in range(0, len(plans), size)]
    results = {}
    with mp.get_context('fork').Pool(parts, initializer=_init,
                                     initargs=(plans, tables, scales)) as pool:
        for rows in pool.imap_unordered(_run, [chunk for chunk in work if chunk]):
            for row in rows:
                results[row['episode']] = row
    if len(results) != len(plans):
        raise ValueError(f'scored {len(results)} of {len(plans)} episodes')
    written = write_records(output / 'records.jsonl.gz', [results[i] for i in range(len(plans))])
    write_json(output / 'COMPLETED.json', dict(
        status='scored; aggregation pending', episodes=len(plans), records=written,
        records_sha256=file_hash(output / 'records.jsonl.gz'),
        elapsed_seconds=time.perf_counter() - started))
    print(f'wrote {written} records to {output}')


if __name__ == '__main__':
    main()
