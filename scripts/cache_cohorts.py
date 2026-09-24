"""Build each cohort's merged evidence once and cache it.

A cohort accumulator is the frozen per-record file plus the newly scored
classical baselines plus the unified network's records.  Streaming all three
every time a table is rebuilt is wasteful, so the merge is cached per cohort and
reused by the table builder and the interval runs.
"""
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.aggregate import add_records, load_accumulator, save_accumulator, stream_records  # noqa: E402
from unified.workspace import ARCHIVE, file_hash  # noqa: E402

CACHE = ROOT / 'runs/cache_v1'
CACHE.mkdir(parents=True, exist_ok=True)

COHORTS = {
    'public/confirmation': ('round3_fixed_public_retrospective_original_v1', 'bl_public_test', 'conf_public_g16'),
    'public/validation': (None, 'bl_public_val', 'val_g16'),
    'reference/confirmation': ('round3_fixed_reference_confirmation_round3_main_v1', 'bl_reference_conf', 'conf_reference_v7_all'),
    'reference/boundary': ('round3_fixed_reference_boundary_round3_edge_v1', 'bl_reference_bnd', 'bnd_reference_v7_all'),
    'to_asap7/confirmation': ('round3_fixed_to_asap7_confirmation_round3_main_v1', 'bl_to_asap7_conf', 'conf_to_asap7_gap2_all'),
    'to_asap7/boundary': ('round3_fixed_to_asap7_boundary_round3_edge_v1', 'bl_to_asap7_bnd', 'bnd_to_asap7_gap2_to_asap7_all'),
    'to_freepdk15/confirmation': ('round3_fixed_to_freepdk15_confirmation_round3_main_v1', 'bl_to_freepdk15_conf', 'conf_to_freepdk15_gap2_all'),
    'to_freepdk15/boundary': ('round3_fixed_to_freepdk15_boundary_round3_edge_v1', 'bl_to_freepdk15_bnd', 'bnd_to_freepdk15_gap2_to_freepdk15_all'),
    'reference/validation': (None, 'bl_reference_val', 'reference_val_v7_all'),
    'to_asap7/validation': (None, 'bl_to_asap7_val', 'to_asap7_val_v6_all'),
    'to_freepdk15/validation': (None, 'bl_to_freepdk15_val', 'to_freepdk15_val_gap2_all'),
}


def main():
    wanted = sys.argv[1:] or sorted(COHORTS)
    for name in wanted:
        if name not in COHORTS:
            raise SystemExit(f'unknown cohort {name}')
        frozen, baselines, unified = COHORTS[name]
        cache = CACHE / (name.replace('/', '_') + '.json')
        if cache.exists():
            print(f'{name}: cached')
            continue
        extras = []
        if frozen:
            extras.append(ARCHIVE / 'runs' / frozen / 'records.jsonl.gz')
        for folder in (baselines, unified):
            path = ROOT / 'runs' / folder / 'records.jsonl.gz'
            if not path.exists():
                print(f'{name}: waiting for {folder}')
                continue
            extras.append(path)
        if not extras:
            print(f'{name}: nothing to merge')
            continue
        started = time.perf_counter()
        accumulator = stream_records(extras[0])
        for path in extras[1:]:
            add_records(accumulator, path)
        save_accumulator(accumulator, cache, meta=dict(
            cohort=name, sources=[dict(path=str(p), sha256=file_hash(p)) for p in extras],
            cells=len(accumulator), seconds=time.perf_counter() - started))
        print(f'{name}: {len(accumulator)} cells in {time.perf_counter() - started:.1f}s')
    print('cache complete')


if __name__ == '__main__':
    main()
