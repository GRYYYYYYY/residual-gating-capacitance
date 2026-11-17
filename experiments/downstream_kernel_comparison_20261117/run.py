"""Add the manuscript's OpenRCX kernel to the frozen B4/B8 downstream study.

Same 498 support episodes, 83 tables, eight layouts and seeds 11/29/47.
No training, new support selection, changes to Full, or computeTable injection.
Use --export, then --pilot, then --run --workers 4 after sourcing the DAC env.
"""
from pathlib import Path
import argparse
import collections
import concurrent.futures
import json
import os
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments/dac_characterization_20261114'))
import downstream as prior
from experiments.pex_kernel_revision.kernels import openrcx
from openrcbench.export import export_openrcx

OLD = ROOT / 'results/dac_characterization_20261114/downstream'
OUT = ROOT / 'results/downstream_kernel_comparison_20261117'
SEEDS = (11, 29, 47)
sha, write = prior.sha, prior.write


def export():
    out = OUT / 'rules'
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((OLD / 'rules/manifest.json').read_text())
    tables_path = ROOT / 'runs/public_inventory_holdout_v1/tables.jsonl'
    tables = {t['table_id']: t for t in map(json.loads, tables_path.read_text().splitlines())}
    harness = ROOT / 'results/pex_kernel_revision/pinned_kernel'
    cpp_path = ROOT / 'experiments/pex_kernel_revision/pinned_kernel.cpp'
    extraction = json.loads((ROOT / 'results/pex_kernel_revision/extracted_kernel.json').read_text())
    assert sha(cpp_path) == extraction['harness_sha256']
    write(OUT / 'FROZEN.json', dict(
        baseline='OpenRCX kernel, same operator and scalar component wrapper as Fig. 4',
        support_manifest_sha256=sha(OLD / 'rules/manifest.json'), tables_sha256=sha(tables_path),
        kernel_sha256=sha(ROOT / 'experiments/pex_kernel_revision/kernels.py'),
        harness_sha256=sha(harness), harness_source_sha256=sha(cpp_path),
        source_commit=extraction['source_commit'], native_tcl_sha256=sha(prior.HERE / 'native.tcl'),
        script_sha256=sha(__file__), method='openrcx_kernel', budgets=[4, 8], seeds=SEEDS,
        preservation='only nonobserved coupling/ground entries in identical eligible tables; observed rows and resistance retained',
        geometry='table represented coordinates, GF180 scale 2000, others 1000; same as coverage.py',
        scope='fixed-node rule completion followed by unchanged native extraction/STA; no online neural or computeTable injection',
        resources=dict(max_workers=4, threads_per_openroad=1, timeout_per_run_s=300, native_runs=48, training_runs=0)))
    checks, exports = [], []
    payloads = {(b, s): {'tables': {}} for b in (4, 8) for s in SEEDS}
    for entry in manifest['support']:
        t = tables[entry['table_id']]
        x, y = np.asarray(t['coordinates']), np.asarray(t['labels'])
        o = entry['support']; q = np.setdiff1d(np.arange(len(x)), o)
        assert t['family'] in ('OVER', 'UNDER', 'OVERUNDER', 'DIAGUNDER')
        assert all(n in ('coupling_cap', 'ground_cap') for n in t['target_names'])
        scale = 2000. if t['process_id'] == 'gf180' else 1000.
        pred, meta = openrcx(x[o], y[o], x[q], scale=scale)
        # Check every exported query with the extracted pinned C++ function bodies.
        ws = np.unique(x[o, 0]); lines = ['1', f'{len(ws)} {len(q)} 0']
        for w in ws:
            ids = np.array(o)[x[o, 0] == w]; ids = ids[np.argsort(x[ids, 1])]
            lines.append(f'{int(np.floor(w * scale + .5))} {len(ids)}')
            for i in ids:
                yy = np.pad(y[i], (0, 3 - y.shape[1]))
                lines.append(' '.join(map(str, [int(np.floor(x[i, 1] * scale + .5)), *yy])))
        for i in q:
            lines.append(f'{int(np.floor(x[i, 0] * scale + .5))} {int(np.floor(x[i, 1] * scale + .5))}')
        text = '\n'.join(lines) + '\n'
        result = subprocess.run([str(harness)], input=text, text=True, capture_output=True, check=True, timeout=10)
        cpp = np.array([[float(v) for v in line.split()] for line in result.stdout.splitlines()])
        np.testing.assert_array_equal(cpp[:, :2], [[a['width_index'], a['effective_separation']] for a in meta])
        norm = max(float(np.max(abs(y[o]))), 1e-30)
        err = float(np.max(abs(pred - cpp[:, 2:2 + y.shape[1]])) / norm)
        assert err < 1e-12 and np.isfinite(pred).all() and (pred >= 0).all()
        key = entry['budget_requested'], entry['seed']
        payloads[key]['tables'][entry['upstream_id']] = {
            str(i): {name: float(pred[j, k]) for k, name in enumerate(t['target_names'])} for j, i in enumerate(q)}
        checks.append(dict(**entry, family=t['family'], process=t['process_id'], coordinate_scale=scale,
                           max_cpp_python_scaled_error=err, exported_queries=len(q),
                           paths=dict(collections.Counter(a['path'] for a in meta))))
    for (budget, seed), payload in payloads.items():
        name = f'openrcx_kernel_B{budget}_s{seed}'
        path = out / f'{name}.json'; write(path, payload)
        reference = json.loads((OLD / f'rules/cmi_B{budget}_s{seed}.json').read_text())['tables']
        assert payload['tables'].keys() == reference.keys()
        for tid in reference:
            assert payload['tables'][tid].keys() == reference[tid].keys()
        for platform, source_id, relative in prior.SOURCES:
            original = prior.UP / 'data/raw' / relative
            dest = out / platform / f'{name}.rules'
            receipt = export_openrcx(original, prior.UP / 'data/processed/dataset.jsonl', path, dest, source_id=source_id)
            old = next(e for e in manifest['exports'] if e['platform'] == platform and e['method'] == 'cmi' and e['budget'] == budget and e['seed'] == seed)
            assert receipt['changed_rows'] == old['changed_rows']
            assert sha(original) == old['original_sha256']
            exports.append(dict(name=name, method='openrcx_kernel', platform=platform, budget=budget,
                                seed=seed, path=str(dest), sha256=sha(dest), original=str(original),
                                original_sha256=sha(original), **receipt))
    write(out / 'manifest.json', dict(exports=exports, support=manifest['support'], eligible_tables=83,
                                     excluded_short_tables=manifest['excluded_short_tables']))
    write(OUT / 'kernel_validation.json', dict(passed=True, episodes=len(checks),
          queries=sum(r['exported_queries'] for r in checks),
          max_scaled_error=max(r['max_cpp_python_scaled_error'] for r in checks), checks=checks))
    print('Exported 24 rule files; all 498 support episodes validated against C++.', flush=True)


def run(pilot, workers):
    assert 1 <= workers <= 4
    frozen = json.loads((OUT / 'FROZEN.json').read_text())
    assert sha(OLD / 'rules/manifest.json') == frozen['support_manifest_sha256']
    assert sha(prior.HERE / 'native.tcl') == frozen['native_tcl_sha256']
    entries = json.loads((OUT / 'rules/manifest.json').read_text())['exports']
    prior.R = OUT
    tasks = []
    for case in sorted(prior.CASES):
        golden = OUT / 'native' / case / 'golden'
        golden.parent.mkdir(parents=True, exist_ok=True)
        if not golden.exists():
            golden.symlink_to(OLD / 'native' / case / 'golden', target_is_directory=True)
        assert golden.resolve() == OLD / 'native' / case / 'golden'
        for e in entries:
            if e['platform'] != case.split('/')[0]: continue
            if pilot and (case != 'asap7/ibex' or e['budget'] != 8 or e['seed'] != 11): continue
            assert sha(e['path']) == e['sha256']
            completed = OUT / 'native' / case / e['name'] / 'COMPLETED.json'
            if completed.exists():
                assert json.loads(completed.read_text())['status'] == 'ok'
                assert json.loads((completed.parent / 'FROZEN.json').read_text())['provenance']['rules'] == e['sha256']
                continue
            tasks.append((case, e['name'], Path(e['path'])))
    start = time.perf_counter(); failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(prior.native, *task): task for task in tasks}
        for job in concurrent.futures.as_completed(jobs):
            try:
                value = job.result()
                if value['status'] != 'ok': failures.append((jobs[job][:2], value))
            except Exception as exc:
                failures.append((jobs[job][:2], repr(exc)))
    completed = list((OUT / 'native').glob('*/*/openrcx_kernel*/COMPLETED.json'))
    report = dict(pilot=pilot, new_runs=len(tasks), completed=len(completed),
                  failed=failures, elapsed_seconds=time.perf_counter() - start, workers=workers)
    write(OUT / ('PILOT.json' if pilot else 'COMPLETED.json'), report)
    print(json.dumps(report, indent=2), flush=True)
    assert not failures
    if not pilot: assert len(completed) == 48


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--export', action='store_true')
    group.add_argument('--pilot', action='store_true')
    group.add_argument('--run', action='store_true')
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    if args.export: export()
    else: run(args.pilot, args.workers)
