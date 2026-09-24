"""Collect every reported cohort into one machine-readable summary."""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from unified.workspace import new_run, write_json  # noqa: E402

REPORTS = {
    'public/confirmation': 'report_public_confirmation_v2',
    'reference/confirmation': 'report_reference_confirmation_v1',
    'to_asap7/confirmation': 'report_to_asap7_confirmation_v3',
    'to_freepdk15/confirmation': 'report_to_freepdk15_confirmation_v3',
    'reference/boundary': 'report_reference_boundary_v1',
    'to_asap7/boundary': 'report_to_asap7_boundary_v1',
    'to_freepdk15/boundary': 'report_to_freepdk15_boundary_v1',
}
SELECTIONS = {
    'public': 'selection_public_v2',
    'reference': 'selection_reference_v2',
    'to_asap7': 'selection_to_asap7_v2',
    'to_freepdk15': 'selection_to_freepdk15_v2',
}


def main():
    payload = {'cohorts': {}, 'selections': {}}
    for name, folder in REPORTS.items():
        path = ROOT / 'runs' / folder / 'COMPLETED.json'
        if not path.exists():
            payload['cohorts'][name] = {'status': 'not_completed', 'expected': folder}
            continue
        payload['cohorts'][name] = json.loads(path.read_text())
    for name, folder in SELECTIONS.items():
        path = ROOT / 'runs' / folder / 'COMPLETED.json'
        payload['selections'][name] = (json.loads(path.read_text()) if path.exists()
                                       else {'status': 'not_completed', 'expected': folder})
    output = new_run('final_summary_v2')
    write_json(output / 'COMPLETED.json', payload)
    for name, value in payload['cohorts'].items():
        print(f'{name:26s} {value.get("status", "reported")}')
    for name, value in payload['selections'].items():
        print(f'select {name:19s} {value.get("selected", value.get("status"))}')
    print(f'\nwritten to {output}')


if __name__ == '__main__':
    main()
