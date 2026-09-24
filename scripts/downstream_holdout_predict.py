"""Predictions for the RC/STA downstream audit, from this workspace's model.

The audit rewrites the value rows of held-out rule tables in each platform's
OpenRCX rule file, re-extracts the parasitics of a fixed routed design and
re-runs STA.  `prepare_downstream_rules.py` consumes a predictions file in the
``{table_id: {row: {target: value}}}`` form; this produces that file from the
residual-gate ensemble trained on the held-out inventory.

The two inventories key the same rule tables differently, so a table is matched
by content: source id, family, metal, context, corner and the ordered coordinate
sequence.  Matched tables agree on the coordinate order and on every label
exactly, which is what lets the upstream mask indices be used unchanged.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'upstream'))

from unified.score import load_members, predict_table  # noqa: E402
from unified.workspace import new_run  # noqa: E402
from pdkcap.common import read_tables  # noqa: E402
from pdkcap.train import unique_tables  # noqa: E402

from openrcbench.io import read_jsonl  # noqa: E402
from openrcbench.masking import mask_indices  # noqa: E402
from openrcbench.physics import active_targets  # noqa: E402
from openrcbench.schema import TARGET_NAMES  # noqa: E402

UPSTREAM = Path(__import__('os').environ.get('RG_UPSTREAM_ROOT', ROOT / 'upstream')).resolve()
DATASET = UPSTREAM / 'data/processed/dataset.jsonl'
SPLIT = UPSTREAM / 'data/splits/in_domain.json'
HOLDOUT = ROOT / 'runs/public_inventory_holdout_v1/tables.jsonl'

PLATFORM_PREFIX = {
    'asap7': 'orfs_asap7_20260903',
    'ihp-sg13g2': 'orfs_ihp_sg13g2_20260903',
    'sky130hs': 'orfs_sky130hs_20260903',
    'gf180': 'orfs_gf180_20260903:gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules',
}
#: The methods exported per seed.  ``ours`` is the deployed ensemble; ``anchor``
#: is its skip path, carried so the part of any timing change that comes from the
#: table's own interpolant rather than from the learned correction is visible.
METHODS = ('ours', 'anchor')


def study_key(row):
    return (row['source_id'], row['family'], row['metal'], row['context_above'],
            row['context_below'], row['corner_id'],
            tuple(tuple(round(float(v), 9) for v in point) for point in row['coordinates']))


def upstream_key(table):
    """Content key of an upstream ``RCTable``, matching :func:`study_key`."""
    return (table.source_id, table.family, table.metal, table.context_above,
            table.context_below, table.corner_id,
            tuple((round(float(table.width), 9), round(float(r['spacing_left']), 9),
                   round(float(r['spacing_right']), 9)) for r in table.rows))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', action='append', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ratios', type=float, nargs='+', default=[.3, .5])
    parser.add_argument('--seeds', type=int, nargs='+', default=[0, 1, 2])
    args = parser.parse_args()

    tables = unique_tables(read_tables(HOLDOUT))
    by_key = {study_key(t): t for t in tables}
    # RCTable objects, not dicts: mask_indices reads table.rows.
    dataset = read_jsonl(DATASET)
    test_ids = set(json.loads(SPLIT.read_text())['test'])
    prefixes = set(PLATFORM_PREFIX.values())

    scored = [table for table in dataset
              if table.source_id in prefixes and table.table_id in test_ids]
    pairs, unmatched = [], []
    for table in scored:
        match = by_key.get(upstream_key(table))
        (pairs if match is not None else unmatched).append((table, match))
    if unmatched:
        print(f'  {len(unmatched)} upstream tables have no held-out counterpart; skipped')

    members, scales = load_members([str(Path(p).resolve()) for p in args.checkpoint])
    output = new_run(args.output)
    manifest = {'checkpoints': args.checkpoint, 'members': len(members),
                'scope': 'held-out rule tables only; block masks; fixed routed layouts',
                'matched_tables': len(pairs), 'unmatched_upstream_tables': len(unmatched),
                'ratios': args.ratios, 'seeds': args.seeds, 'methods': list(METHODS),
                'unmodelled_active_targets': 'resistance is constant across rows on every '
                                            'scored table, so it is left at golden',
                'files': []}

    #: Targets this estimator models.  The upstream audit's tables also carry a
    #: resistance column, but on every scored table it is constant across rows,
    #: so the golden value is already the correct one and the exporter leaving it
    #: alone is the right behaviour rather than a gap.  Tables whose only active
    #: target is resistance therefore receive no predictions at all, which the
    #: count below records rather than hides.
    skipped = collections.Counter()

    for ratio in args.ratios:
        for seed in args.seeds:
            payload = {method: {'tables': {}} for method in METHODS}
            for upstream, study in pairs:
                hidden = mask_indices(upstream, 'block', ratio, seed)
                observed = np.array(sorted(set(range(len(study['coordinates']))) - hidden), int)
                if len(observed) == 0:
                    raise ValueError(f'no observed rows for {upstream.table_id}')
                labels = np.asarray(study['labels'], float)
                prediction, anchor, _, _ = predict_table(
                    members, scales, study, observed, labels[observed])
                active = active_targets(upstream.rows, TARGET_NAMES)
                index = {name: position for position, name in enumerate(study['target_names'])}
                predicted = tuple(target for target in active if target in index)
                for target in active:
                    if target not in index:
                        skipped[target] += 1
                if not predicted:
                    skipped['table with no modelled target'] += 1
                    continue
                for method, values in (('ours', prediction), ('anchor', anchor)):
                    payload[method]['tables'][upstream.table_id] = {
                        str(row): {target: float(values[row][index[target]]) for target in predicted}
                        for row in sorted(hidden)}
            for method in METHODS:
                name = f'{method}_block{int(ratio * 100)}_seed{seed}'
                path = output / f'{name}.json'
                path.write_text(json.dumps(payload[method], indent=2) + '\n')
                manifest['files'].append(dict(name=name, method=method, ratio=ratio,
                                              seed=seed, path=str(path),
                                              tables=len(payload[method]['tables'])))
                print(f'  wrote {name}: {len(payload[method]["tables"])} tables')

    manifest['skipped'] = dict(skipped)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'  skipped targets/cells: {dict(skipped)}')
    print(f'wrote {output}')


if __name__ == '__main__':
    main()
