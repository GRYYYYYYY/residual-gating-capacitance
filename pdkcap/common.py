from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ('OVER', 'UNDER', 'OVERUNDER', 'DIAGUNDER')
TARGETS = ('coupling_cap', 'ground_cap')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    serialized=json.dumps(value, indent=2, allow_nan=False)+'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        f.write(serialized)


def read_tables(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
