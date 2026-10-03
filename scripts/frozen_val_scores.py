"""Score the frozen policies on the validation cohort, for like-for-like selection.

The frozen validation shards already carry every expert's prediction on the same
episodes the unified network is scored on, plus the validation-frozen
segment/component map.  Rebuilding ``linear`` and ``SACE-Select`` from those
shards lets the configuration choice be made against the deployment policy that
actually won selection, not against a proxy.  Read-only.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unified.aggregate import SEED_BY_METHOD, mask_macro_nrmse  # noqa: E402
from unified.workspace import ARCHIVE, file_hash, new_run, write_json  # noqa: E402

from pdkcap.round3_support import SEGMENTS  # noqa: E402

FOLDERS = {
    'public': 'runs/round3_public_validation_records_v1',
    'reference': 'runs/round3_reference_validation_records_v1',
    'to_asap7': 'runs/round3_to_asap7_validation_records_v1',
}
BUNDLES = {
    'public': 'runs/round3_public_deployment_v1/bundle.json',
    'reference': 'runs/round3_reference_deployment_v1/bundle.json',
    'to_asap7': 'runs/round3_to_asap7_deployment_v1/bundle.json',
}


def accumulate(folder, selection, expert_names):
    """Mask-macro accumulator for linear, the frozen map, and every single expert."""
    receipt = json.loads((folder / 'COMPLETED.json').read_text())
    names = list(receipt['expert_names'])
    if names != list(expert_names):
        raise ValueError('expert order differs from the deployment selection')
    linear = names.index('linear')
    selected = np.asarray(selection['selected'], int)
    accumulator = {}
    for shard in receipt['shards']:
        if file_hash(shard['path']) != shard['sha256'] or file_hash(shard['metadata']) != shard['metadata_sha256']:
            raise ValueError('validation shard drift')
        meta = json.loads(Path(shard['metadata']).read_text())
        if meta['partition'] != 'val':
            raise ValueError('non-validation shard')
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
            # The frozen map chooses an expert per (query, component); an
            # inapplicable choice falls back to linear on that component only.
            pick = selected[segment_episode]
            rows, columns = np.indices(pick.shape)
            chosen = np.where(valid_episode[rows, pick], pick, linear)
            methods = {'linear': deployed[:, linear, :],
                       'fixed': deployed[rows, chosen, columns]}
            for position, name in enumerate(names):
                methods[name] = deployed[:, position, :]
            for method, values in methods.items():
                error = ((values - truth_episode) ** 2).sum(axis=0)
                energy = (truth_episode ** 2).sum(axis=0)
                cell = (method, SEED_BY_METHOD.get(method, 'none'), meta['process'], meta['family'],
                        case['protocol'], case['ratio'], int(case['mask_seed']), 'all')
                entry = accumulator.get(cell)
                if entry is None:
                    entry = accumulator[cell] = {'n': 0, 'se': np.zeros(len(error)), 'sy': np.zeros(len(error))}
                entry['n'] += len(truth_episode)
                entry['se'] += error
                entry['sy'] += energy
    return accumulator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', choices=sorted(FOLDERS), required=True)
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()
    folder = ARCHIVE / FOLDERS[args.domain]
    bundle = json.loads((ARCHIVE / BUNDLES[args.domain]).read_text())
    accumulator = accumulate(folder, bundle['fixed_selection'], bundle['expert_selection_names']
                             if 'expert_selection_names' in bundle else _names(folder))
    report = {}
    for method in ['linear', 'fixed', 'original_dro', 'hard_local', 'gated_none']:
        report[method] = {protocol: mask_macro_nrmse(accumulator, method, protocol, .3)
                          for protocol in ('mcar', 'block', 'extrapolation')}
    print(json.dumps(report, indent=1))
    if args.output:
        output = new_run(args.output)
        write_json(output / 'COMPLETED.json', dict(domain=args.domain, folder=str(folder),
                                                   folder_receipt_sha256=file_hash(folder / 'COMPLETED.json'),
                                                   scores=report,
                                                   scope='validation cohort only; no test labels'))


def _names(folder):
    return json.loads((folder / 'COMPLETED.json').read_text())['expert_names']


if __name__ == '__main__':
    main()
