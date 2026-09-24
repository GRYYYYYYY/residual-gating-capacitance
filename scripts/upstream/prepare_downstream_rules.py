#!/usr/bin/env python3
"""Export held-out-table block completions using completed model-v2 predictions."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openrcbench.baselines import interpolate_table
from openrcbench.export import export_openrcx
from openrcbench.io import read_jsonl
from openrcbench.masking import mask_indices
from openrcbench.physics import active_targets
from openrcbench.schema import TARGET_NAMES


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    dataset = Path('data/processed/dataset.jsonl')
    tables = {t.table_id: t for t in read_jsonl(dataset)}
    test_ids = set(json.loads(Path('data/splits/in_domain.json').read_text())['test'])
    sources = [
        ('asap7', 'orfs_asap7_20260903', 'asap7/rcx_patterns.rules'),
        ('gf180', 'orfs_gf180_20260903:gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules', 'gf180/gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules'),
        ('ihp-sg13g2', 'orfs_ihp_sg13g2_20260903', 'ihp_sg13g2/IHP_rcx_patterns.rules'),
        ('sky130hs', 'orfs_sky130hs_20260903', 'sky130/rcx_patterns.rules'),
    ]
    root = Path('runs/downstream/rules')
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'scope': 'block masks on in-domain test tables only; all other tables retain golden truth',
                'inactive_targets': 'preserve structurally absent targets as golden zero; not prediction tasks',
                'physics_lambda': 0.05, 'dataset_sha256': digest(dataset), 'exports': []}
    for platform, source_id, relative in sources:
        original = Path('data/raw') / relative
        source_tables = [t for t in tables.values() if t.source_id == source_id]
        selected = [t for t in source_tables if t.table_id in test_ids]
        golden = root / platform / 'golden.rules'
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_bytes(original.read_bytes())
        for seed in range(3):
            for ratio in (0.3, 0.5):
                prediction_path = Path(f'runs/model_v2/proposed/seed{seed}/block_{ratio}_predictions.json')
                predictions = json.loads(prediction_path.read_text())['tables']
                if set(predictions) != test_ids:
                    raise ValueError(f'Unexpected prediction table set: {prediction_path}')
                for method in ('model', 'linear'):
                    payload = {'tables': {}}
                    for table in selected:
                        hidden = mask_indices(table, 'block', ratio, seed)
                        if set(map(int, predictions[table.table_id])) != hidden:
                            raise ValueError(f'Mask mismatch: {table.table_id}')
                        active = active_targets(table.rows, TARGET_NAMES)
                        values = predictions[table.table_id] if method == 'model' else {
                            str(i): row for i, row in enumerate(interpolate_table(table.rows, hidden, 'linear')) if i in hidden}
                        payload['tables'][table.table_id] = {
                            str(i): {target: values[str(i)][target] for target in active} for i in sorted(hidden)}
                    name = f'{method}_block{int(ratio*100)}_seed{seed}'
                    prediction_export = golden.parent / f'{name}.json'
                    prediction_export.write_text(json.dumps(payload, indent=2)+'\n')
                    output = golden.parent / f'{name}.rules'
                    result = export_openrcx(original, dataset, prediction_export, output, source_id=source_id)
                    manifest['exports'].append(dict(platform=platform, source_id=source_id, method=method,
                        seed=seed, ratio=ratio, original=str(original), original_sha256=digest(original),
                        output=str(output), output_sha256=digest(output), prediction_file=str(prediction_path) if method=='model' else None,
                        prediction_sha256=digest(prediction_path) if method=='model' else None,
                        test_tables=len(selected), total_tables=len(source_tables),
                        source_rows=sum(len(t.rows) for t in source_tables), **result))
    root.joinpath('manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f"Verified {len(manifest['exports'])} completed rule files; four golden copies")

if __name__ == '__main__':
    main()
