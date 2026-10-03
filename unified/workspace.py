"""Repository paths and read-only access to released input artifacts.

Set RG_DATA_ROOT to use an external artifact installation. New runs are
created under the repository's runs directory without overwriting inputs.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path(os.environ.get('RG_DATA_ROOT', ROOT)).resolve()
VENV_PYTHON = Path(sys.executable)

FAMILIES = ('OVER', 'UNDER', 'OVERUNDER', 'DIAGUNDER')
SEGMENTS = ('outside', 'missing_width', 'dense_1d', 'dense_nd', 'sparse_or_degenerate')

# ---------------------------------------------------------------------------
# Fixed dataset paths used by the released experiment configurations.
# ---------------------------------------------------------------------------
INPUTS = {
    'public_tables': ARCHIVE / 'runs/public_inventory_v1/tables.jsonl',
    'reference_val_tables': ARCHIVE / 'runs/round3_reference_dataset_v1/tables.jsonl',
    'reference_train_tables': ARCHIVE / 'runs/reference_dataset_v2/tables.jsonl',
    'round2_reference_tables': ARCHIVE / 'runs/round2_reference_dataset_v1/tables.jsonl',
}
FROZEN_PROTOCOL = ROOT / 'configs/round3_protocol.json'


def archive_on_path():
    """Import the frozen package read-only; safe to call repeatedly."""
    text = str(ARCHIVE)
    if text not in sys.path:
        sys.path.insert(0, text)
    return ARCHIVE


archive_on_path()


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    """Exclusive create: refuses to overwrite an existing artifact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as handle:
        handle.write(json.dumps(value, indent=2, allow_nan=False) + '\n')
    return path


def read_json(path):
    return json.loads(Path(path).read_text())


def new_run(name):
    """Fresh immutable run directory; hard failure when the name is taken."""
    path = ROOT / 'runs' / name
    path.mkdir(parents=True, exist_ok=False)
    return path


def source_hashes(extra=()):
    paths = sorted(ROOT.glob('unified/*.py')) + [Path(p) for p in extra]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths if Path(p).exists()}


def os_threads(n):
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = str(n)


def input_hashes():
    """Hash the frozen inputs actually consumed, for run receipts."""
    kinds = {}
    for name, path in INPUTS.items():
        kinds[name] = dict(path=str(path), sha256=file_hash(path))
    kinds['round3_protocol'] = dict(path=str(FROZEN_PROTOCOL), sha256=file_hash(FROZEN_PROTOCOL))
    return kinds
