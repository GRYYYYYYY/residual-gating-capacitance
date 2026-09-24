"""Unified, split-aware access to the released capacitance databases."""
from pathlib import Path
import json
import os

ROOT=Path(__file__).resolve().parents[1]

def catalog():
    return json.loads((ROOT/'database/catalog.json').read_text())

def load_tables(dataset, partition='train', root=None):
    """Read table dictionaries without merging sources or changing numerical values.

    The default is the training partition, never the full data. Pass a named
    evaluation partition deliberately, or partition=None for explicit audit use.
    """
    item=catalog()['datasets'][dataset]
    if item.get('kind') != 'tables':
        raise ValueError(f'{dataset} is not a table dataset; inspect the catalog')
    base=Path(root or os.environ.get('RG_DATA_ROOT', ROOT))
    path=base/item['path']
    if not path.exists():
        raise FileNotFoundError(f'{path}: run python -m capdata fetch database')
    if partition is not None and partition not in item['partitions']:
        raise ValueError(f'{dataset}: available partitions are {list(item["partitions"])}')
    with path.open() as f:
        rows=[json.loads(line) for line in f if line.strip()]
    return rows if partition is None else [r for r in rows if r['partition']==partition]
