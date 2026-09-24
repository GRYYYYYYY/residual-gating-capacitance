"""Write this workspace's predictions into OpenRCX rule files, in a new tree.

Same export path as the upstream audit -- ``openrcbench.export.export_openrcx``,
which substitutes only the listed target values on the listed rows and leaves
every other byte of the rule file alone -- but it reads the predictions produced
by ``downstream_holdout_predict.py`` and writes under
``runs/downstream_holdout_v1/``.  The upstream ``runs/downstream/`` tree is left
untouched, so the two audits stay separately attributable.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = Path(__import__('os').environ.get('RG_UPSTREAM_ROOT', ROOT / 'upstream')).resolve()
sys.path.insert(0, str(UPSTREAM))

from openrcbench.export import export_openrcx  # noqa: E402

DATASET = UPSTREAM / 'data/processed/dataset.jsonl'

#: (platform, source id, path under data/raw), the four rule files the audit
#: rewrites.  Same four the upstream audit uses.
SOURCES = (
    ('asap7', 'orfs_asap7_20260903', 'asap7/rcx_patterns.rules'),
    ('gf180', 'orfs_gf180_20260903:gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules',
     'gf180/gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules'),
    ('ihp-sg13g2', 'orfs_ihp_sg13g2_20260903', 'ihp_sg13g2/IHP_rcx_patterns.rules'),
    ('sky130hs', 'orfs_sky130hs_20260903', 'sky130/rcx_patterns.rules'),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--predictions', required=True,
                        help='run directory holding <method>_block<r>_seed<s>.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    predictions_dir = ROOT / 'runs' / args.predictions
    manifest_in = json.loads((predictions_dir / 'manifest.json').read_text())
    output = ROOT / 'runs' / args.output
    output.mkdir(parents=True, exist_ok=False)

    manifest = {'scope': 'held-out rule tables only; all other tables retain golden truth',
                'predictions': args.predictions,
                'predictions_manifest_sha256': digest(predictions_dir / 'manifest.json'),
                'dataset_sha256': digest(DATASET), 'exports': []}

    for platform, source_id, relative in SOURCES:
        original = UPSTREAM / 'data/raw' / relative
        folder = output / platform
        folder.mkdir(parents=True)
        golden = folder / 'golden.rules'
        golden.write_bytes(original.read_bytes())
        for entry in manifest_in['files']:
            name = entry['name']
            prediction_export = folder / f'{name}.json'
            prediction_export.write_text(
                (predictions_dir / f'{name}.json').read_text())
            rules = folder / f'{name}.rules'
            result = export_openrcx(original, DATASET, prediction_export, rules,
                                    source_id=source_id)
            manifest['exports'].append(dict(
                platform=platform, source_id=source_id, name=name,
                method=entry['method'], ratio=entry['ratio'], seed=entry['seed'],
                original=str(original), original_sha256=digest(original),
                prediction=str(prediction_export), prediction_sha256=digest(prediction_export),
                output=str(rules), output_sha256=digest(rules), **result))
            print(f'  {platform}/{name}: {result}')

    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'wrote {output} ({len(manifest["exports"])} rule files)')


if __name__ == '__main__':
    main()
