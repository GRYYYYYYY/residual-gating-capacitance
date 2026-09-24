"""Re-extract and re-time one fixed layout under this workspace's rule files.

Same mechanism as the upstream audit's ``run_downstream_reextraction.py``: the
golden routed snapshot and constraints are copied into a fresh flow variant, so
``do-6_report`` re-runs extraction and STA on an unchanged routed database and
skips synthesis, placement and routing entirely.  Everything that could move a
timing number except the rule file is therefore held fixed, and the rule file is
the only thing this audit varies.

Outputs go under ``runs/downstream_holdout_v1/comparisons/`` with a distinct
flow tag, so the upstream ``runs/downstream/`` evidence is neither read as
provenance nor overwritten.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = Path(__import__('os').environ.get('RG_UPSTREAM_ROOT', ROOT / 'upstream')).resolve()
sys.path.insert(0, str(UPSTREAM))

from openrcbench.spef import compare_spef  # noqa: E402

RUN_TAG_PREFIX = 'rcgate'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', required=True,
                        choices=['asap7', 'gf180', 'ihp-sg13g2', 'sky130hs'])
    parser.add_argument('--design', required=True, choices=['aes', 'ibex'])
    parser.add_argument('--rules-run', default='downstream_holdout_v1')
    parser.add_argument('--golden-tag', default='golden_20260909')
    args = parser.parse_args()

    flow = UPSTREAM / 'tools/OpenROAD-flow-scripts/flow'
    result_base = flow / 'results' / args.platform / args.design
    golden = result_base / args.golden_tag
    snapshot = golden / '6_1_fill.odb'
    constraints = golden / '6_1_fill.sdc'
    if not all(p.exists() for p in (snapshot, constraints, golden / '6_final.spef')):
        raise ValueError('golden routed snapshot, constraints and SPEF are required')

    rules_root = ROOT / 'runs' / args.rules_run
    manifest = json.loads((ROOT / 'runs' / args.rules_run / 'manifest.json').read_text())
    output = ROOT / 'runs' / args.rules_run / 'comparisons' / args.platform / args.design
    output.mkdir(parents=True, exist_ok=True)
    hook = UPSTREAM / 'scripts' / ('time_extraction_gf180.tcl'
                                   if args.platform == 'gf180' else 'time_extraction.tcl')

    variants = [dict(name='golden', method='golden', output=str(rules_root / args.platform / 'golden.rules'))]
    variants += [dict(name=e['name'], method=e['method'], output=e['output'],
                      output_sha256=e['output_sha256'], ratio=e['ratio'], seed=e['seed'])
                 for e in manifest['exports'] if e['platform'] == args.platform]

    reference_spef = None
    for variant in variants:
        name = variant['name']
        tag = f'{RUN_TAG_PREFIX}_{name}_20260924'
        destination = result_base / tag
        rules = Path(variant['output'])
        if variant.get('output_sha256') and sha(rules) != variant['output_sha256']:
            raise ValueError('rule artifact hash mismatch')
        state = output / f'{name}.json'
        provenance = dict(
            routed_database_sha256=sha(snapshot), constraints_sha256=sha(constraints),
            rules_sha256=sha(rules), openroad_sha256=sha(os.environ['OPENROAD_EXE']),
            timing_hook_sha256=sha(hook), num_cores=os.environ.get('NUM_CORES'),
            corner='TC' if args.platform == 'gf180' else os.environ.get('CORNER', 'platform_default'))
        spef = destination / '6_final.spef'
        if state.exists():
            previous = json.loads(state.read_text())
            if previous['provenance'] != provenance or not spef.is_file() \
                    or previous['spef_sha256'] != sha(spef):
                raise ValueError(f'resume provenance mismatch: {state}')
            if name == 'golden':
                reference_spef = spef
            print(f'  reused verified {args.platform}/{args.design}/{name}', flush=True)
            continue

        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot, destination / snapshot.name)
        shutil.copy2(constraints, destination / constraints.name)
        if (golden / 'memories').is_dir():
            shutil.copytree(golden / 'memories', destination / 'memories', dirs_exist_ok=True)

        common = ['make', '--no-print-directory', '-C', str(flow),
                  f'DESIGN_CONFIG=designs/{args.platform}/{args.design}/config.mk',
                  f'FLOW_VARIANT={tag}', f'RCX_RULES={rules}',
                  f'PRE_FINAL_REPORT_TCL={hook}']
        if args.platform == 'gf180':
            common.append('CORNER=TC')
        probe = (".PHONY: openrcbench-print-rcx\nopenrcbench-print-rcx:\n"
                 "\t@printf '%s\\n' '$(RCX_RULES)'\n")
        resolved = subprocess.check_output(common + ['-s', '--eval=' + probe,
                                                     'openrcbench-print-rcx'], text=True).strip()
        if resolved != str(rules):
            raise ValueError('RCX_RULES resolution mismatch')
        log = output / f'{name}.log'
        with log.open('w') as handle:
            subprocess.run(common + ['do-6_report'], stdout=handle,
                           stderr=subprocess.STDOUT, check=True)
        if not spef.is_file():
            raise ValueError('missing extracted SPEF')
        raw = log.read_text()
        timings = re.findall(r'OPENRCBENCH_EXTRACTION_SECONDS ([0-9.]+)', raw)
        memory = re.findall(r'Peak memory: ([0-9]+)KB', raw)
        if len(timings) != 1 or not memory:
            raise ValueError('missing extraction/runtime evidence')

        if name == 'golden':
            replay = compare_spef(golden / '6_final.spef', spef, output / 'golden_replay_check.json')
            if not (replay['common_nets'] == replay['golden_nets'] == replay['candidate_nets']):
                raise ValueError('golden replay network set changed')
            if any(replay['metrics'][t]['rmse'] != 0 for t in ('capacitance', 'resistance')):
                raise ValueError('golden replay changed extracted parasitics')
            reference_spef = spef
        metrics_file = flow / 'logs' / args.platform / args.design / tag / '6_report.json'
        metrics = json.loads(metrics_file.read_text())
        comparison = compare_spef(reference_spef, spef, output / f'{name}_spef.json')
        if comparison['common_nets'] != comparison['golden_nets'] \
                or comparison['common_nets'] != comparison['candidate_nets']:
            raise ValueError('network set differs on the shared routed design')
        state.write_text(json.dumps(dict(
            platform=args.platform, design=args.design,
            variant={k: variant[k] for k in ('name', 'method') if k in variant}
            | {k: variant[k] for k in ('ratio', 'seed') if k in variant},
            provenance=provenance, spef=str(spef), spef_sha256=sha(spef),
            extraction_seconds=float(timings[0]),
            final_report_process_peak_kb=int(memory[-1]),
            timing_metrics=metrics, comparison=comparison), indent=2) + '\n')
        print(f'  completed {args.platform}/{args.design}/{name}: '
              f'{comparison["common_nets"]} nets', flush=True)


if __name__ == '__main__':
    main()
