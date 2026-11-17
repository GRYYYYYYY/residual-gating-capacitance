"""Rebuild Table III and Fig. 5 from completed, matched MLI/Full native runs.

Run with the repository's experiments/dac_characterization_20261114/env.sh.
--collect creates a portable raw-input bundle once; normal runs use that bundle.
No model fitting, extraction, STA, or source-result mutation is performed.
"""
from pathlib import Path
import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import math
import re
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import MaxNLocator

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.pex_kernel_revision.kernels import mli, independent_axes

D = P / 'data/downstream_matched_mli'
SOURCE = 'results/dac_characterization_20261114/downstream'
SEEDS = (11, 29, 47)
CASES = [('asap7', 'ASAP7'), ('gf180', 'GF180'),
         ('ihp-sg13g2', 'IHP-SG13G2'), ('sky130hs', 'Sky130HS')]
METHODS = ('cmi', 'full')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def collect():
    D.mkdir(parents=True, exist_ok=True)
    if (D / 'raw_inputs.json.gz').exists():
        raise FileExistsError('Raw input bundle already exists; reuse without --collect')
    files = {}

    def add(path):
        files[path] = (ROOT / path).read_text()

    add(SOURCE + '/rules/manifest.json')
    add('runs/public_inventory_holdout_v1/tables.jsonl')
    add('results/dac_characterization_20261114/summary/downstream_raw.csv')
    for budget in (4, 8):
        for seed in SEEDS:
            add(f'{SOURCE}/rules/cmi_B{budget}_s{seed}.json')
    for platform, _ in CASES:
        for design in ('aes', 'ibex'):
            variants = ['golden'] + [f'{m}_B{b}_s{s}' for m in METHODS
                                     for b in (4, 8) for s in SEEDS]
            for variant in variants:
                base = f'{SOURCE}/native/{platform}/{design}/{variant}/'
                for name in ('COMPLETED.json', 'FROZEN.json'):
                    add(base + name)
                if variant == 'golden':
                    add(base + 'native.log')
                if design == 'ibex' and (variant == 'golden' or '_B8_' in variant):
                    for name in ('endpoints.tsv', 'layout.tsv', 'ports.tsv', 'bounds.tsv'):
                        add(base + name)
    bundle = json.dumps(files, sort_keys=True).encode()
    (D / 'raw_inputs.json.gz').write_bytes(gzip.compress(bundle, mtime=0))
    receipt = dict(source_root=str(ROOT), files={k: digest(v.encode()) for k, v in files.items()},
                   bundle_sha256=digest(bundle), scope='Completed B4/B8 fixed-node rule-export runs')
    (D / 'sources.json').write_text(json.dumps(receipt, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--collect', action='store_true')
    if ap.parse_args().collect:
        collect()
    bundle = gzip.decompress((D / 'raw_inputs.json.gz').read_bytes())
    receipt = json.loads((D / 'sources.json').read_text())
    assert digest(bundle) == receipt['bundle_sha256']
    raw = json.loads(bundle)
    assert all(digest(raw[k].encode()) == v for k, v in receipt['files'].items())

    def obj(path):
        return json.loads(raw[path])

    def tsv(path):
        return list(csv.DictReader(io.StringIO(raw[path]), delimiter='\t'))

    manifest = obj(SOURCE + '/rules/manifest.json')
    tables = {t['table_id']: t for t in map(json.loads, raw['runs/public_inventory_holdout_v1/tables.jsonl'].splitlines())}
    # Prove that the archived CMI values equal the manuscript's actual MLI-ext.
    # operator on EVERY exported row/component, rather than equating method names.
    max_delta = 0.0
    checked = 0
    ranks, policies = collections.Counter(), collections.Counter()
    for entry in manifest['support']:
        t = tables[entry['table_id']]
        x = np.asarray(t['coordinates']); o = entry['support']; v = np.asarray(t['labels'])[o]
        ranks[len(independent_axes(x[o]))] += 1
        pred, status = mli(x[o], v, x, extension=True)
        pred = np.maximum(pred, 0); pred[o] = v
        policies.update(status)
        payload = obj(f"{SOURCE}/rules/cmi_B{entry['budget_requested']}_s{entry['seed']}.json")['tables'][entry['upstream_id']]
        assert set(map(int, payload)) == set(range(len(x))) - set(o)
        for i, values in payload.items():
            expected = np.array([values[k] for k in t['target_names']])
            np.testing.assert_allclose(pred[int(i)], expected, rtol=1e-10, atol=1e-14)
            max_delta = max(max_delta, float(np.max(abs(pred[int(i)] - expected))))
            checked += len(expected)
    assert len(manifest['support']) == 498 and ranks == {1: 498}
    exports = {(e['platform'], e['name']): e for e in manifest['exports']}
    old = list(csv.DictReader(io.StringIO(raw['results/dac_characterization_20261114/summary/downstream_raw.csv'])))
    old = {(r['case'], r['method'], int(r['budget']), int(r['data_seed'])): r for r in old}
    records, panels, spatial_seeds = [], [], []
    for platform, title in CASES:
        for design in ('aes', 'ibex'):
            case = f'{platform}/{design}'
            base = f'{SOURCE}/native/{case}/'
            gold = obj(base + 'golden/COMPLETED.json')
            provenance = obj(base + 'golden/FROZEN.json')['provenance']
            unit = re.search(r'\btime 1(\w+)', raw[base + 'golden/native.log'])[1]
            scale = {'ps': .001, 'ns': 1., 'us': 1000.}[unit]
            assert gold['status'] == 'ok'
            assert gold['comparison']['metrics']['capacitance']['rmse'] == 0
            errors = {}
            if design == 'ibex':
                endpoints = {r['endpoint']: float(r['slack']) * scale * 1000 for r in tsv(base + 'golden/endpoints.tsv')}
                ids = sorted(k for k, v in endpoints.items() if np.isfinite(v))
                gold_y = np.array([endpoints[k] for k in ids])
                canon = lambda s: s.replace('\\', '')
                loc = {canon(r['instance']): ((float(r['xmin']) + float(r['xmax'])) / 2,
                       (float(r['ymin']) + float(r['ymax'])) / 2) for r in tsv(base + 'golden/layout.tsv')}
                ports = {canon(r['port']): (float(r['x']), float(r['y'])) for r in tsv(base + 'golden/ports.tsv')}
                xy = np.array([ports[canon(k)] if canon(k) in ports else loc[canon(k).rsplit('/', 1)[0]] for k in ids])
            for budget in (4, 8):
                for seed in SEEDS:
                    for method in METHODS:
                        variant = f'{method}_B{budget}_s{seed}'
                        p = base + variant + '/'
                        state = obj(p + 'COMPLETED.json'); frozen = obj(p + 'FROZEN.json')['provenance']
                        assert state['status'] == 'ok'
                        assert all(frozen[k] == provenance[k] for k in ('odb', 'sdc', 'openroad', 'libs', 'tcl'))
                        assert frozen['rules'] == exports[platform, variant]['sha256']
                        assert exports[platform, variant]['original_sha256'] == provenance['rules']
                        comp = state['comparison']
                        assert comp['metrics']['resistance']['rmse'] == 0
                        assert comp['common_nets'] == comp['golden_nets'] == comp['candidate_nets']
                        rec = dict(case=case, method=method, budget=budget, seed=seed,
                                   net_cap_nrmse=comp['metrics']['capacitance']['nrmse'],
                                   ws_abs_ns=abs(state['worst_slack_native'] - gold['worst_slack_native']) * scale,
                                   tns_abs_ns=abs(state['tns_native'] - gold['tns_native']) * scale)
                        for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns'):
                            np.testing.assert_allclose(rec[field], float(old[case, method, budget, seed][field]), rtol=1e-12, atol=1e-15)
                        records.append(rec)
                        if design == 'ibex' and budget == 8:
                            for geom in ('layout.tsv', 'ports.tsv', 'bounds.tsv'):
                                assert raw[p + geom] == raw[base + 'golden/' + geom]
                            e = {r['endpoint']: float(r['slack']) * scale * 1000 for r in tsv(p + 'endpoints.tsv')}
                            assert set(e) == set(endpoints)
                            assert sorted(k for k, v in e.items() if np.isfinite(v)) == ids
                            y = np.array([e[k] for k in ids])
                            np.testing.assert_allclose(y.min(), state['worst_slack_native'] * scale * 1000, atol=.002, rtol=0)
                            # Match the archived STA audit's 0.02-native-unit
                            # tolerance for accumulated, printed endpoint slacks.
                            np.testing.assert_allclose(np.minimum(y, 0).sum(), state['tns_native'] * scale * 1000, atol=.02 * scale * 1000, rtol=0)
                            err = abs(y - gold_y); errors[method, seed] = err
                            np.testing.assert_allclose(err.mean(), float(old[case, method, budget, seed]['slack_mae_ns']) * 1000, rtol=1e-10, atol=1e-10)
            if design == 'ibex':
                mean_mli = np.mean([errors['cmi', s] for s in SEEDS], axis=0)
                mean_full = np.mean([errors['full', s] for s in SEEDS], axis=0)
                for seed in SEEDS:
                    l, f = errors['cmi', seed].mean(), errors['full', seed].mean()
                    spatial_seeds.append(dict(case=case, seed=seed, mli_mae_ps=float(l), full_mae_ps=float(f), reduction_pct=float(100 * (1 - f / l))))
                bounds = np.loadtxt(io.StringIO(raw[base + 'golden/bounds.tsv']))
                edges = [np.linspace(bounds[i], bounds[i + 2], 51) for i in (0, 1)]
                counts = np.histogram2d(xy[:, 0], xy[:, 1], bins=edges)[0]
                assert counts.sum() == len(ids)
                gain = mean_mli - mean_full
                sums = np.histogram2d(xy[:, 0], xy[:, 1], bins=edges, weights=gain)[0]
                grid = np.ma.masked_where(counts.T == 0, (sums / np.maximum(counts, 1)).T)
                rec = dict(case=case, endpoints=len(ids), mli_mae_ps=float(mean_mli.mean()),
                           full_mae_ps=float(mean_full.mean()), reduction_pct=float(100 * (1 - mean_full.mean() / mean_mli.mean())))
                panels.append((title, bounds, edges, grid, rec))
                stream = io.StringIO(); w = csv.writer(stream)
                w.writerow(['endpoint', 'x_um', 'y_um', 'mli_error_ps', 'full_error_ps', 'gain_ps'])
                w.writerows((k, *coord, l, f, g) for k, coord, l, f, g in zip(ids, xy, mean_mli, mean_full, gain))
                (D / f'{platform}_endpoint_seedmean.csv.gz').write_bytes(gzip.compress(stream.getvalue().encode(), mtime=0))
    assert len(records) == 96
    groups = collections.defaultdict(list)
    for r in records:
        groups[r['case'], r['budget'], r['method']].append(r)
    reductions = []
    for platform, _ in CASES:
        for design in ('aes', 'ibex'):
            for b in (4, 8):
                result = dict(case=f'{platform}/{design}', budget=b)
                for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns'):
                    vals = []
                    for m in METHODS:
                        rs = groups[result['case'], b, m]; assert len(rs) == 3
                        vals.append(float(np.mean([r[field] for r in rs])))
                    l, f = vals
                    result[field + '_mli'], result[field + '_full'] = l, f
                    assert l > 0 or f == 0
                    result[field + '_reduction_pct'] = 100 * (1 - f / l) if l else None
                reductions.append(result)
    lines = [r'\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lrrr@{}}', r'\toprule',
             r'Layout & Cap. & $|\Delta\mathrm{WS}|$ & $|\Delta\mathrm{TNS}|$ \\', r'\midrule']
    for platform, title in CASES:
        for design in ('aes', 'ibex'):
            pair = [r for r in reductions if r['case'] == f'{platform}/{design}']
            values = []
            for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns'):
                a = [r[field + '_reduction_pct'] for r in pair]
                values.append('/'.join('--' if v is None else f'{v:.1f}' for v in a))
            lines.append(title.replace('IHP-SG13G2', 'IHP') + '/' + design.upper() + ' & ' + ' & '.join(values) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular*}']
    (P / 'tables/downstream_matched_mli.tex').write_text('\n'.join(lines) + '\n')
    for name, rs in [('native_metrics.csv', records), ('reductions.csv', reductions), ('spatial_seeds.csv', spatial_seeds)]:
        with (D / name).open('w') as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0])); w.writeheader(); w.writerows(rs)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7, 'axes.titlesize': 7.5, 'pdf.fonttype': 42})
    fig, axs = plt.subplots(2, 2, figsize=(3.45, 3.15), layout='constrained')
    fig.set_constrained_layout_pads(w_pad=.015, h_pad=.01, wspace=.025, hspace=.04)
    for ax, (title, bounds, edges, grid, r) in zip(axs.ravel(), panels):
        ax.set(xlim=(bounds[0], bounds[2]), ylim=(bounds[1], bounds[3]), aspect='equal')
        ax.set_title(title + ' / IBEX', pad=4)
        ax.xaxis.set_major_locator(MaxNLocator(3)); ax.yaxis.set_major_locator(MaxNLocator(3))
        ax.tick_params(labelsize=6, pad=1, length=2); ax.set_facecolor('#ededed')
        for spine in ax.spines.values(): spine.set_color('#9aa5af')
        gmax = float(np.max(abs(grid))); unit = 10 ** math.floor(math.log10(gmax)); lim = math.ceil(gmax / unit) * unit
        im = ax.pcolormesh(*edges, grid, cmap='RdBu', norm=TwoSlopeNorm(0, -lim, lim), shading='flat', rasterized=True)
        cb = fig.colorbar(im, ax=ax, fraction=.05, pad=.025); cb.set_ticks([-lim, 0, lim])
        cb.ax.tick_params(labelsize=6, pad=1, length=2); cb.ax.set_title('ps', fontsize=6.5, pad=3)
        ax.text(.02, .98, f"MAE {r['mli_mae_ps']:.2f} → {r['full_mae_ps']:.2f} ps", transform=ax.transAxes,
                va='top', fontsize=5.7, bbox=dict(facecolor='white', alpha=.9, edgecolor='none', pad=1))
    fig.supxlabel(r'$x$ ($\mu$m)', fontsize=7); fig.supylabel(r'$y$ ($\mu$m)', fontsize=7)
    for ext in ('pdf', 'png'):
        fig.savefig(P / f'figures/downstream_matched_mli.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    report = dict(native_runs=96, golden_runs=8, support_episodes=498, checked_prediction_components=checked,
                  max_mli_archive_absolute_difference=max_delta, ranks=dict(ranks), policies=dict(policies),
                  seeds=SEEDS, budgets=[4, 8], spatial_budget=8, spatial=[r[-1] for r in panels],
                  spatial_seed_improvements=sum(r['reduction_pct'] > 0 for r in spatial_seeds),
                  wins={field: sum(r[field + '_reduction_pct'] is not None and r[field + '_reduction_pct'] > 0 for r in reductions)
                        for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns')},
                  evidence='Native frozen rule hashes, same ODB/SDC/libraries/OpenROAD, unchanged R, identical endpoint sets and geometry',
                  scope='Fixed-node rule export; MLI-ext. verified on this cohort; no computeTable or commercial-product claim')
    (D / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
