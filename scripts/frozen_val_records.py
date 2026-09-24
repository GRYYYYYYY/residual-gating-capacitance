"""Rebuild frozen-policy records on the validation cohort, in the scored schema.

The frozen validation shards already carry every expert's prediction on exactly
the episodes the unified network is scored on, together with the
validation-frozen segment/component map.  Re-emitting them as records in the
same schema as :mod:`unified.score` makes the validation comparison paired and
aggregated by one identical function, instead of comparing a rebuilt number
against a published one.  Read-only on the frozen workspace.
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unified.aggregate import SEED_BY_METHOD  # noqa: E402
from unified.workspace import ARCHIVE, file_hash, new_run, write_json  # noqa: E402

from pdkcap.common import read_tables  # noqa: E402
from pdkcap.metrics import record  # noqa: E402
from pdkcap.round2_model import load_checkpoint  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

FOLDERS = {
    'public': 'runs/round3_public_validation_records_v1',
    'reference': 'runs/round3_reference_validation_records_v1',
    'to_asap7': 'runs/round3_to_asap7_validation_records_v1',
    'to_freepdk15': 'runs/round3_to_freepdk15_validation_records_v1',
}
BUNDLES = {
    'public': 'runs/round3_public_deployment_v1/bundle.json',
    'reference': 'runs/round3_reference_deployment_v1/bundle.json',
    'to_asap7': 'runs/round3_to_asap7_deployment_v1/bundle.json',
    'to_freepdk15': 'runs/round3_to_freepdk15_deployment_v1/bundle.json',
}
INPUTS = {name: ARCHIVE / f'runs/round3_validation_inputs_v1/{name}_val.jsonl' for name in FOLDERS}
DEFAULT_METHODS = ('linear', 'fixed', 'original_dro', 'hard_local', 'gated_none')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', choices=sorted(FOLDERS), required=True)
    parser.add_argument('--output', type=str, required=True)
    parser.add_argument('--methods', nargs='+', default=list(DEFAULT_METHODS))
    args = parser.parse_args()

    folder = ARCHIVE / FOLDERS[args.domain]
    bundle = json.loads((ARCHIVE / BUNDLES[args.domain]).read_text())
    selection = bundle['fixed_selection']
    receipt = json.loads((folder / 'COMPLETED.json').read_text())
    names = [name for name in receipt['expert_names']]
    if names != list(selection['expert_names']):
        raise ValueError('expert order differs between shards and deployment selection')
    tables = {table['table_id']: table for table in unique_tables(read_tables(INPUTS[args.domain]))}
    linear = names.index('linear')
    selected = np.asarray(selection['selected'], int)
    scales = load_checkpoint(bundle['expert_bundle']['methods']['original_dro']['checkpoints'][0])[1]

    output = new_run(args.output)
    write_json(output / 'FROZEN.json', dict(
        domain=args.domain, folder=str(folder), folder_receipt_sha256=file_hash(folder / 'COMPLETED.json'),
        bundle=str(BUNDLES[args.domain]), methods=list(args.methods),
        scope='validation cohort rebuilt from frozen shards; no frozen run was re-executed'))
    written = 0
    with gzip.open(output / 'records.jsonl.gz', 'wt') as handle:
        for shard in receipt['shards']:
            if file_hash(shard['path']) != shard['sha256'] or file_hash(shard['metadata']) != shard['metadata_sha256']:
                raise ValueError('validation shard drift')
            meta = json.loads(Path(shard['metadata']).read_text())
            if meta['partition'] != 'val':
                raise ValueError('non-validation shard')
            table = tables[meta['table_id']]
            with np.load(shard['path'], allow_pickle=False) as data:
                prediction = data['prediction']
                truth = data['truth']
                valid = data['valid']
                segment = data['segment']
                episode = data['episode']
            for index, case in enumerate(meta['episodes']):
                take = episode == index
                if not take.any():
                    raise ValueError(f'episode {index} absent from {shard["path"]}')
                truth_episode = truth[take]
                prediction_episode = prediction[take]
                valid_episode = valid[take]
                segment_episode = segment[take]
                deployed = np.where(valid_episode[:, :, None], prediction_episode,
                                    prediction_episode[:, linear:linear + 1, :])
                pick = selected[segment_episode]
                rows, columns = np.indices(pick.shape)
                chosen = np.where(valid_episode[rows, pick], pick, linear)
                values = {'linear': deployed[:, linear, :], 'fixed': deployed[rows, chosen, columns]}
                for name in args.methods:
                    if name in values:
                        continue
                    if name not in names:
                        raise ValueError(f'unknown frozen method {name}')
                    values[name] = deployed[:, names.index(name), :]
                for name in args.methods:
                    payload = record(table, truth_episode, values[name], episode=index, method=name,
                                     training_seed=SEED_BY_METHOD.get(name, 'none'),
                                     protocol=case['protocol'], ratio=case['ratio'],
                                     mask_seed=int(case['mask_seed']), segment='all',
                                     requested_n=len(truth_episode), coverage=1.0,
                                     scored_indices=case['scored'],
                                     training_scale=np.asarray(
                                         scales['targets'][table['family']], float).tolist(),
                                     dependency_group=table.get('split_group', table['table_id']))
                    handle.write(json.dumps(payload, allow_nan=False) + '\n')
                    written += 1
    write_json(output / 'COMPLETED.json', dict(status='frozen validation records rebuilt', records=written,
                                               methods=list(args.methods), domain=args.domain))
    print(f'{args.domain}: {written} records -> {output}')


if __name__ == '__main__':
    main()
