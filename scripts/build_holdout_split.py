"""Build a public-rule inventory that holds out the downstream-scored tables.

The RC/STA downstream audit masks the rule tables that are in the openrcbench
in-domain *test* split and present in each platform's rule file.  Those tables
are not held out by the study's own train/val/test split -- 55 of the 84 land in
the study's training partition -- so a model trained on the frozen inventory has
already seen most of what the audit would score it on.

This writes a derived inventory in which those tables are moved to a `holdout`
partition, so neither training stage can read them.  Nothing in the frozen
archive is touched; the output is a new file under this workspace's runs/.

Tables are matched by content, not by id: the two inventories key the same rule
tables with different hashes, but agree on source id, family, metal, context,
corner and the ordered coordinate sequence.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.workspace import ARCHIVE  # noqa: E402

FROZEN_INVENTORY = ARCHIVE / 'runs/public_inventory_v1/tables.jsonl'
UPSTREAM = Path(__import__('os').environ.get('RG_UPSTREAM_ROOT', ROOT / 'upstream')).resolve()
DATASET = UPSTREAM / 'data/processed/dataset.jsonl'
SPLIT = UPSTREAM / 'data/splits/in_domain.json'
OUTPUT = ROOT / 'runs/public_inventory_holdout_v1/tables.jsonl'

#: (platform, source-id prefix) of the rule files the downstream audit rewrites.
PLATFORM_PREFIX = {
    'asap7': 'orfs_asap7_20260903',
    'ihp-sg13g2': 'orfs_ihp_sg13g2_20260903',
    'sky130hs': 'orfs_sky130hs_20260903',
    'gf180': 'orfs_gf180_20260903:gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules',
}


def study_key(row):
    return (row['source_id'], row['family'], row['metal'], row['context_above'],
            row['context_below'], row['corner_id'],
            tuple(tuple(round(float(v), 9) for v in point) for point in row['coordinates']))


def upstream_key(row):
    return (row['source_id'], row['family'], row['metal'], row['context_above'],
            row['context_below'], row['corner_id'],
            tuple((round(float(row['width']), 9), round(float(r['spacing_left']), 9),
                   round(float(r['spacing_right']), 9)) for r in row['rows']))


def main():
    inventory = [json.loads(line) for line in FROZEN_INVENTORY.open() if line.strip()]
    dataset = [json.loads(line) for line in DATASET.open() if line.strip()]
    test_ids = set(json.loads(SPLIT.read_text())['test'])

    scored_source_ids = set()
    for platform, prefix in PLATFORM_PREFIX.items():
        scored_source_ids.add(prefix)
    upstream_scored = [row for row in dataset
                       if row['source_id'] in scored_source_ids and row['table_id'] in test_ids]

    study_by_key = {study_key(row): row for row in inventory}
    held = set()
    unmatched = []
    for row in upstream_scored:
        match = study_by_key.get(upstream_key(row))
        if match is None:
            unmatched.append(row['table_id'])
        else:
            held.add(match['table_id'])

    output = []
    moved = collections.Counter()
    for row in inventory:
        row = dict(row)
        if row['table_id'] in held:
            moved[row['partition']] += 1
            row['partition'] = 'holdout'
        output.append(row)

    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    with OUTPUT.open('w') as handle:
        for row in output:
            handle.write(json.dumps(row) + '\n')

    after = collections.Counter(row['partition'] for row in output)
    print(f'frozen inventory rows: {len(inventory)}')
    print(f'upstream tables scored downstream: {len(upstream_scored)} '
          f'({len(upstream_scored) - len(unmatched)} matched, {len(unmatched)} unmatched)')
    print(f'held out: {sum(moved.values())} rows, from partitions {dict(moved)}')
    print(f'output partitions: {dict(after)}')
    print(f'wrote {OUTPUT}')


if __name__ == '__main__':
    main()
