"""Score the unified network on a frozen evaluation cohort.

Records are written in exactly the schema produced by the frozen Round-3 fixed
scorer (`metrics.record` plus the same episode metadata), so a new model's
evidence merges with the archived baseline accumulation and both are aggregated
by one identical function.  Episode enumeration is the frozen one
(`pdkcap.round2_train.episodes`); masks are re-derived deterministically from
(protocol, ratio, seed) so work spreads across processes without changing the
episode order or the mask content.
"""
import argparse
import gzip
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

from .basis import CLASSICAL
from .episodes import encode, stack
from .model import ResidualGateNet, SelectGate
from .workspace import (file_hash, input_hashes, new_run, os_threads,
                        source_hashes, write_json)
from .workspace import archive_on_path

archive_on_path()

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.metrics import record  # noqa: E402
from pdkcap.round2_train import episodes  # noqa: E402
from pdkcap.round3_support import SEGMENTS  # noqa: E402
from pdkcap.sampling import mask  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

WORKER = {}


def load_members(paths, gate_map=None):
    """Load checkpoints; ``gate_map`` freezes the gate to the archived map instead.

    Two architecture generations are routable: the original gate
    (``sace-r-v1``) and the dictionary-attention gate (``rg-*``).  The version
    string in the checkpoint decides, so archived runs keep scoring through the
    code path that produced them.
    """
    import torch
    from .estimator import ResidualGatingEstimator
    members, scales = [], None
    for path in paths:
        state = torch.load(path, map_location='cpu', weights_only=True)
        settings = dict(targets=state['targets'], features_in=state['features_in'],
                        gate_in=state['gate_in'], experts=state['experts'],
                        width=state['width'], layers=state['layers'],
                        gate_hidden=state['gate_hidden'],
                        anchor_logit_gap=state['anchor_logit_gap'],
                        agreement=state.get('agreement', False))
        if state.get('version') == ResidualGateNet.version:
            model = (SelectGate(gate_map, **settings) if gate_map is not None
                     else ResidualGateNet(**settings))
        elif str(state.get('version', '')).startswith('rg-'):
            if gate_map is not None:
                raise ValueError('the dictionary-attention gate has no archived map to freeze to')
            # The descriptor width is read off the checkpoint rather than
            # assumed: an older generation of this gate used fewer channels, and
            # loading it with today's constant silently mismatches the key.
            width = state['state_dict']['key.weight'].shape[1]
            model = ResidualGatingEstimator(head_dim=state['head_dim'],
                                            channels=state.get('channels', width),
                                            **settings)
        else:
            raise ValueError(f'unknown unified checkpoint version in {path}')
        model.load_state_dict(state['state_dict'])
        model.eval()
        members.append(model)
        scales = state['scales'] if scales is None else scales
        if state['scales'] != scales:
            raise ValueError('members disagree on training scales')
    return members, scales


def predict_table(members, scales, table, observed, values, basis=CLASSICAL):
    import torch
    target_scales = np.asarray(scales['targets'][table['family']], float)
    encoded = encode(table, observed, values, scales, basis)
    batch = stack([encoded])
    outputs = []
    with torch.inference_mode():
        for model in members:
            prediction = model(batch['features'], batch['anchor'], batch['gate'], batch['delta'],
                               batch['valid'], padding=batch['padding'], clamp_lower=batch['lower'],
                               clamp_upper=batch['upper'], inside=batch['inside'])
            outputs.append(prediction[0, :encoded['n']].numpy() * target_scales)
    output = np.mean(outputs, axis=0)
    output[observed] = values
    anchor = encoded['anchor'][:encoded['n']].astype(float) * target_scales
    anchor[observed] = values
    return output, anchor, encoded['segment'], target_scales


def plan_episodes(tables):
    """Frozen episode enumeration, stored as (table index, protocol, ratio, seed)."""
    lookup = {table['table_id']: index for index, table in enumerate(tables)}
    plans = []
    for table, protocol, ratio, seed, _, _ in episodes(tables):
        plans.append((lookup[table['table_id']], protocol, ratio, seed))
    return plans


def episode_chunks(count, parts):
    size = (count + parts - 1) // parts
    return [list(range(start, min(start + size, count))) for start in range(0, count, size)]


def _init(checkpoints, plans, tables, gate_map=None, basis=CLASSICAL):
    os_threads(1)
    import torch
    torch.set_num_threads(1)
    WORKER['members'], WORKER['scales'] = load_members(checkpoints, gate_map)
    WORKER['plans'], WORKER['tables'], WORKER['basis'] = plans, tables, basis


def _run(chunk):
    members, scales = WORKER['members'], WORKER['scales']
    tables, plans = WORKER['tables'], WORKER['plans']
    rows = []
    for episode_id in chunk:
        table_index, protocol, ratio, seed = plans[episode_id]
        table = tables[table_index]
        truth = np.asarray(table['labels'], float)
        observed, query = mask(table['coordinates'], protocol, ratio, seed)
        prediction, anchor, segment, target_scales = predict_table(
            members, scales, table, observed, truth[observed], WORKER['basis'])
        rows.append(dict(episode=episode_id, table=table, protocol=protocol, ratio=ratio, mask_seed=seed,
                         observed=observed, query=query, segment=segment, truth=truth,
                         prediction=prediction, anchor=anchor, training_scale=target_scales))
    return rows


def dependency_group(table):
    if table['domain'] != 'ctf_derived_2d':
        return table.get('split_group', table['table_id'])
    return f"{table['process_id']}-layer{table['metal']}"


def write_records(path, ordered, method):
    """One record per (episode, method, support region), frozen schema."""
    written = 0
    with gzip.open(path, 'wt') as handle:
        for row in ordered:
            truth = row['truth']
            segment, query = row['segment'], row['query']
            regions = [('all', query)] + [(name, query[segment[query] == index])
                                          for index, name in enumerate(SEGMENTS)]
            for name, prediction in ((method, row['prediction']),
                                     (f'{method}_anchor', row['anchor'])):
                for region, requested in regions:
                    if not len(requested):
                        continue
                    payload = record(row['table'], truth[requested], prediction[requested],
                                     episode=row['episode'], method=name, training_seed='ensemble',
                                     protocol=row['protocol'], ratio=row['ratio'],
                                     mask_seed=row['mask_seed'], segment=region,
                                     requested_n=len(requested), coverage=1.0,
                                     scored_indices=requested.tolist(),
                                     training_scale=np.asarray(row['training_scale'], float).tolist(),
                                     dependency_group=dependency_group(row['table']))
                    handle.write(json.dumps(payload, allow_nan=False) + '\n')
                    written += 1
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--method', type=str, default='sace_r')
    parser.add_argument('--basis', nargs='+', default=list(CLASSICAL),
                        help='classical corrections to compute; the rest are masked out of the gate')
    parser.add_argument('--gate-map', type=Path, default=None,
                        help='freeze the gate to the archived hard map (Select-as-gate check)')
    args = parser.parse_args()
    for path in [args.cohort, *args.checkpoint]:
        if not path.exists():
            raise FileNotFoundError(path)

    output = new_run(args.output)
    tables = unique_tables(read_tables(args.cohort))
    plans = plan_episodes(tables)
    partitions = sorted({table['partition'] for table in tables})
    if len(partitions) != 1:
        raise ValueError(f'cohort mixes partitions: {partitions}')
    write_json(output / 'FROZEN.json', dict(
        cohort=str(args.cohort), cohort_sha256=file_hash(args.cohort),
        checkpoints=[dict(path=str(p), sha256=file_hash(p)) for p in args.checkpoint],
        method=args.method, tables=len(tables), episodes=len(plans), workers=args.workers,
        partitions=partitions,
        sources=source_hashes(), inputs=input_hashes(),
        label_access='masked support only for prediction; query truth used for scoring only'))

    gate_map = None
    if args.gate_map is not None:
        gate_map = json.loads(args.gate_map.read_text())['fixed_selection']['selected']
    started = time.perf_counter()
    parts = max(1, min(args.workers, len(plans)))
    work = [chunk for chunk in episode_chunks(len(plans), parts) if chunk]
    results = {}
    if parts == 1:
        _init(args.checkpoint, plans, tables, gate_map, tuple(args.basis))
        for chunk in work:
            for row in _run(chunk):
                results[row['episode']] = row
    else:
        with mp.get_context('fork').Pool(parts, initializer=_init,
                                         initargs=(args.checkpoint, plans, tables, gate_map, tuple(args.basis))) as pool:
            for rows in pool.imap_unordered(_run, work):
                for row in rows:
                    results[row['episode']] = row
    if len(results) != len(plans):
        raise ValueError(f'scored {len(results)} of {len(plans)} episodes')
    written = write_records(output / 'records.jsonl.gz', [results[i] for i in range(len(plans))], args.method)
    write_json(output / 'COMPLETED.json', dict(
        status='scored; aggregation pending', method=args.method, episodes=len(plans), records=written,
        tables=len(tables), checkpoints=[str(p) for p in args.checkpoint],
        records_sha256=file_hash(output / 'records.jsonl.gz'),
        elapsed_seconds=time.perf_counter() - started))


if __name__ == '__main__':
    main()
