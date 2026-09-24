#!/usr/bin/env python3
"""Compare rule completions on a single immutable routed design, with resume checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openrcbench.spef import compare_spef


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['asap7', 'gf180', 'ihp-sg13g2', 'sky130hs'], required=True)
    parser.add_argument('--design', choices=['aes', 'ibex'], required=True)
    parser.add_argument('--golden-tag', default='golden_20260909')
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    flow = project / 'tools/OpenROAD-flow-scripts/flow'
    result_base = flow / 'results' / args.platform / args.design
    golden = result_base / args.golden_tag
    snapshot = golden / '6_1_fill.odb'
    constraints = golden / '6_1_fill.sdc'
    if not all(p.is_file() for p in (snapshot, constraints, golden / '6_final.spef')):
        raise ValueError('Golden routed snapshot, constraints and SPEF are required')
    output = project / 'runs/downstream/comparisons' / args.platform / args.design
    output.mkdir(parents=True, exist_ok=True)
    hook = project / 'scripts' / ('time_extraction_gf180.tcl' if args.platform == 'gf180' else 'time_extraction.tcl')
    manifest = json.loads((project / 'runs/downstream/rules/manifest.json').read_text())
    variants = [dict(method='golden', output=f'runs/downstream/rules/{args.platform}/golden.rules')]
    variants += [r for r in manifest['exports'] if r['platform'] == args.platform]
    reference_spef = None
    for variant in variants:
        name = 'golden' if variant['method'] == 'golden' else Path(variant['output']).stem
        tag = 'rcaudit_' + name + '_20260909'
        destination = result_base / tag
        rules = project / variant['output']
        if variant.get('output_sha256') and sha(rules) != variant['output_sha256']:
            raise ValueError('Prepared rule artifact hash mismatch')
        state = output / f'{name}.json'
        provenance = dict(routed_database_sha256=sha(snapshot), constraints_sha256=sha(constraints),
                          rules_sha256=sha(rules), openroad_sha256=sha(os.environ['OPENROAD_EXE']),
                          timing_hook_sha256=sha(hook),
                          num_cores=os.environ.get('NUM_CORES'),
                          corner='TC' if args.platform == 'gf180' else os.environ.get('CORNER', 'platform_default'))
        spef = destination / '6_final.spef'
        if state.exists():
            previous = json.loads(state.read_text())
            if previous['provenance'] != provenance or not spef.is_file() or previous['spef_sha256'] != sha(spef):
                raise ValueError(f'Resume provenance mismatch: {state}')
            if name == 'golden': reference_spef = spef
            print(f'Reused verified {args.platform}/{args.design}/{name}', flush=True)
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
        if args.platform == 'gf180': common.append('CORNER=TC')
        probe = ".PHONY: openrcbench-print-rcx\nopenrcbench-print-rcx:\n\t@printf '%s\\n' '$(RCX_RULES)'\n"
        resolved = subprocess.check_output(common + ['-s', '--eval='+probe, 'openrcbench-print-rcx'], text=True).strip()
        if resolved != str(rules): raise ValueError('RCX_RULES resolution mismatch')
        log = output / f'{name}.log'
        with log.open('w') as handle:
            subprocess.run(common + ['do-6_report'], stdout=handle, stderr=subprocess.STDOUT, check=True)
        if not spef.is_file(): raise ValueError('Missing extracted SPEF')
        raw = log.read_text()
        timings = re.findall(r'OPENRCBENCH_EXTRACTION_SECONDS ([0-9.]+)', raw)
        memory = re.findall(r'Peak memory: ([0-9]+)KB', raw)
        if len(timings) != 1 or not memory: raise ValueError('Missing extraction/runtime evidence')
        if name == 'golden':
            replay = compare_spef(golden / '6_final.spef', spef, output / 'golden_replay_check.json')
            if not (replay['common_nets'] == replay['golden_nets'] == replay['candidate_nets']):
                raise ValueError('Golden replay network set changed')
            if any(replay['metrics'][t]['rmse'] != 0 for t in ('capacitance', 'resistance')):
                raise ValueError('Golden replay changed extracted parasitics')
            reference_spef = spef
        metrics_file = flow / 'logs' / args.platform / args.design / tag / '6_report.json'
        metrics = json.loads(metrics_file.read_text())
        comparison = compare_spef(reference_spef, spef, output / f'{name}_spef.json')
        if comparison['common_nets'] != comparison['golden_nets'] or comparison['common_nets'] != comparison['candidate_nets']:
            raise ValueError('Network set differs on the shared routed design')
        result = dict(platform=args.platform, design=args.design, variant=variant, provenance=provenance,
                      spef=str(spef), spef_sha256=sha(spef), extraction_seconds=float(timings[0]),
                      final_report_process_peak_kb=int(memory[-1]), timing_metrics=metrics, comparison=comparison)
        state.write_text(json.dumps(result, indent=2)+'\n')
        print(f'Completed {args.platform}/{args.design}/{name}: {comparison["common_nets"]} nets', flush=True)

if __name__ == '__main__':
    main()
