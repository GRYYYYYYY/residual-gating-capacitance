"""Matched MLI-ext./OpenRCX kernel downstream table and 2x4 single-column maps.

--collect imports only the new OpenRCX evidence. MLI/Full evidence is read from
the immutable downstream_matched_mli raw bundle. No native execution here.
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

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import MaxNLocator

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
D = P / 'data/downstream_two_kernels'
OLD = 'results/dac_characterization_20261114/downstream'
NEW = 'results/downstream_kernel_comparison_20261117'
CASES = [('asap7', 'ASAP7'), ('gf180', 'GF180'),
         ('ihp-sg13g2', 'IHP-SG13G2'), ('sky130hs', 'Sky130HS')]
SEEDS = (11, 29, 47)
METHODS = ('cmi', 'openrcx_kernel', 'full')
LABELS = {'cmi': 'MLI-ext.', 'openrcx_kernel': 'OpenRCX kernel'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def collect():
    D.mkdir(parents=True, exist_ok=True)
    if (D / 'raw_openrcx.json.gz').exists():
        raise FileExistsError('Raw bundle exists; run without --collect')
    raw = {}
    def add(path): raw[path] = (ROOT / path).read_text()
    for name in ('FROZEN.json', 'COMPLETED.json', 'kernel_validation.json', 'rules/manifest.json'):
        add(NEW + '/' + name)
    done = json.loads(raw[NEW + '/COMPLETED.json'])
    assert done['completed'] == 48 and not done['failed']
    for platform, _ in CASES:
        for design in ('aes', 'ibex'):
            for budget in (4, 8):
                for seed in SEEDS:
                    base = f'{NEW}/native/{platform}/{design}/openrcx_kernel_B{budget}_s{seed}/'
                    for name in ('COMPLETED.json', 'FROZEN.json', 'native.log'):
                        add(base + name)
                    if design == 'ibex' and budget == 8:
                        for name in ('endpoints.tsv', 'layout.tsv', 'ports.tsv', 'bounds.tsv'):
                            add(base + name)
    data = json.dumps(raw, sort_keys=True).encode()
    (D / 'raw_openrcx.json.gz').write_bytes(gzip.compress(data, mtime=0))
    (D / 'sources.json').write_text(json.dumps(dict(source_root=str(ROOT), bundle_sha256=sha(data),
          files={k: sha(v.encode()) for k, v in raw.items()}), indent=2) + '\n')


def load_bundle(folder, name):
    data = gzip.decompress((folder / name).read_bytes())
    sources = json.loads((folder / 'sources.json').read_text())
    assert sha(data) == sources['bundle_sha256']
    raw = json.loads(data)
    assert all(sha(raw[k].encode()) == h for k, h in sources['files'].items())
    return raw


def save_csv(path, rows):
    with path.open('w') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--collect', action='store_true')
    if ap.parse_args().collect: collect()
    raw = load_bundle(P / 'data/downstream_matched_mli', 'raw_inputs.json.gz')
    raw.update(load_bundle(D, 'raw_openrcx.json.gz'))
    obj = lambda p: json.loads(raw[p])
    tsv = lambda p: list(csv.DictReader(io.StringIO(raw[p]), delimiter='\t'))
    old_manifest = obj(OLD + '/rules/manifest.json')
    new_manifest = obj(NEW + '/rules/manifest.json')
    assert old_manifest['support'] == new_manifest['support']
    validation = obj(NEW + '/kernel_validation.json')
    assert validation['passed'] and validation['episodes'] == 498 and validation['max_scaled_error'] < 1e-12
    assert obj(NEW + '/FROZEN.json')['support_manifest_sha256'] == sha(raw[OLD + '/rules/manifest.json'].encode())
    exports = {(e['platform'], e['name']): e for e in old_manifest['exports'] + new_manifest['exports']}
    previous = list(csv.DictReader((P / 'data/downstream_matched_mli/native_metrics.csv').open()))
    previous = {(r['case'], r['method'], int(r['budget']), int(r['seed'])): r for r in previous}
    metrics, spatial, seed_metrics, panels = [], [], [], []
    for platform, title in CASES:
        for design in ('aes', 'ibex'):
            case = f'{platform}/{design}'; goldpath = f'{OLD}/native/{case}/golden/'
            gold = obj(goldpath + 'COMPLETED.json'); frozen_gold = obj(goldpath + 'FROZEN.json')['provenance']
            unit = re.search(r'\btime 1(\w+)', raw[goldpath + 'native.log'])[1]
            scale = {'ps': .001, 'ns': 1., 'us': 1000.}[unit]
            if design == 'ibex':
                gold_ep = {r['endpoint']: float(r['slack']) * scale * 1000 for r in tsv(goldpath + 'endpoints.tsv')}
                ids = sorted(k for k, v in gold_ep.items() if np.isfinite(v))
                gold_y = np.array([gold_ep[k] for k in ids]); errors = {}
                canon = lambda s: s.replace('\\', '')
                loc = {canon(r['instance']): ((float(r['xmin']) + float(r['xmax'])) / 2,
                       (float(r['ymin']) + float(r['ymax'])) / 2) for r in tsv(goldpath + 'layout.tsv')}
                ports = {canon(r['port']): (float(r['x']), float(r['y'])) for r in tsv(goldpath + 'ports.tsv')}
                xy = np.array([ports[canon(k)] if canon(k) in ports else loc[canon(k).rsplit('/', 1)[0]] for k in ids])
            for budget in (4, 8):
                for seed in SEEDS:
                    for method in METHODS:
                        variant = f'{method}_B{budget}_s{seed}'
                        source = NEW if method == 'openrcx_kernel' else OLD
                        path = f'{source}/native/{case}/{variant}/'
                        state = obj(path + 'COMPLETED.json'); prov = obj(path + 'FROZEN.json')['provenance']
                        assert state['status'] == 'ok'
                        assert all(prov[k] == frozen_gold[k] for k in ('odb', 'sdc', 'libs', 'openroad', 'tcl'))
                        assert prov['rules'] == exports[platform, variant]['sha256']
                        assert frozen_gold['rules'] == exports[platform, variant]['original_sha256']
                        comp = state['comparison']
                        assert comp['metrics']['resistance']['rmse'] == 0
                        assert comp['common_nets'] == comp['golden_nets'] == comp['candidate_nets']
                        rec = dict(case=case, method=method, budget=budget, seed=seed,
                                   net_cap_nrmse=comp['metrics']['capacitance']['nrmse'],
                                   ws_abs_ns=abs(state['worst_slack_native'] - gold['worst_slack_native']) * scale,
                                   tns_abs_ns=abs(state['tns_native'] - gold['tns_native']) * scale)
                        if method != 'openrcx_kernel':
                            for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns'):
                                assert rec[field] == float(previous[case, method, budget, seed][field])
                        metrics.append(rec)
                        if design == 'ibex' and budget == 8:
                            for name in ('layout.tsv', 'ports.tsv', 'bounds.tsv'):
                                assert raw[path + name] == raw[goldpath + name]
                            ep = {r['endpoint']: float(r['slack']) * scale * 1000 for r in tsv(path + 'endpoints.tsv')}
                            assert set(ep) == set(gold_ep)
                            assert sorted(k for k, v in ep.items() if np.isfinite(v)) == ids
                            y = np.array([ep[k] for k in ids])
                            np.testing.assert_allclose(y.min(), state['worst_slack_native'] * scale * 1000, atol=.002, rtol=0)
                            np.testing.assert_allclose(np.minimum(y, 0).sum(), state['tns_native'] * scale * 1000, atol=.02 * scale * 1000, rtol=0)
                            errors[method, seed] = abs(y - gold_y)
            if design == 'ibex':
                bounds = np.loadtxt(io.StringIO(raw[goldpath + 'bounds.tsv']))
                edges = [np.linspace(bounds[i], bounds[i + 2], 51) for i in (0, 1)]
                counts = np.histogram2d(xy[:, 0], xy[:, 1], bins=edges)[0]
                assert counts.sum() == len(ids)
                fmean = np.mean([errors['full', s] for s in SEEDS], axis=0)
                rowpanels = []
                for method in METHODS[:2]:
                    bmean = np.mean([errors[method, s] for s in SEEDS], axis=0)
                    gain = bmean - fmean
                    sums = np.histogram2d(xy[:, 0], xy[:, 1], bins=edges, weights=gain)[0]
                    grid = np.ma.masked_where(counts.T == 0, (sums / np.maximum(counts, 1)).T)
                    rec = dict(case=case, baseline=method, endpoints=len(ids), baseline_mae_ps=float(bmean.mean()),
                               full_mae_ps=float(fmean.mean()), reduction_pct=float(100 * (1 - fmean.mean() / bmean.mean())))
                    spatial.append(rec); rowpanels.append((grid, rec))
                    for seed in SEEDS:
                        a, b = errors[method, seed].mean(), errors['full', seed].mean()
                        seed_metrics.append(dict(case=case, baseline=method, seed=seed, baseline_mae_ps=float(a),
                                                 full_mae_ps=float(b), reduction_pct=float(100 * (1 - b / a))))
                    f = io.StringIO(); w = csv.writer(f)
                    w.writerow(['endpoint', 'x_um', 'y_um', 'baseline_error_ps', 'full_error_ps', 'gain_ps'])
                    w.writerows((k, *c, a, b, g) for k, c, a, b, g in zip(ids, xy, bmean, fmean, gain))
                    (D / f'{platform}_{method}_endpoint_seedmean.csv.gz').write_bytes(gzip.compress(f.getvalue().encode(), mtime=0))
                panels.append((title, bounds, edges, rowpanels))
    assert len(metrics) == 144
    groups = collections.defaultdict(list)
    for r in metrics: groups[r['case'], r['budget'], r['method']].append(r)
    reductions = []
    for platform, _ in CASES:
        for design in ('aes', 'ibex'):
            for budget in (4, 8):
                for baseline in METHODS[:2]:
                    case = f'{platform}/{design}'; rec = dict(case=case, budget=budget, baseline=baseline)
                    for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns'):
                        means = []
                        for m in (baseline, 'full'):
                            rs = groups[case, budget, m]; assert len(rs) == 3
                            means.append(float(np.mean([r[field] for r in rs])))
                        a, b = means
                        assert a > 0 or b == 0
                        rec[field + '_baseline'], rec[field + '_full'] = a, b
                        rec[field + '_reduction_pct'] = 100 * (1 - b / a) if a else None
                    reductions.append(rec)
    lines = [r'\begin{tabular*}{\columnwidth}{@{\extracolsep{\fill}}lrrrrrr@{}}', r'\toprule',
             r'& \multicolumn{3}{c}{vs. MLI-ext.} & \multicolumn{3}{c}{vs. OpenRCX kernel} \\',
             r'\cmidrule(lr){2-4}\cmidrule(l){5-7}',
             r'Layout & C & WS & TNS & C & WS & TNS \\', r'\midrule']
    for platform, title in CASES:
        for design in ('aes', 'ibex'):
            values = []
            for baseline in METHODS[:2]:
                rs = [r for r in reductions if r['case'] == f'{platform}/{design}' and r['baseline'] == baseline]
                for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns'):
                    vals = [r[field + '_reduction_pct'] for r in rs]
                    values.append('/'.join('--' if v is None else f'{v:.1f}' for v in vals))
            name = title.replace('IHP-SG13G2', 'IHP').replace('Sky130HS', 'Sky130')
            lines.append(name + '/' + design.upper() + ' & ' + ' & '.join(values) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular*}']
    (P / 'tables/downstream_two_kernels.tex').write_text('\n'.join(lines) + '\n')
    save_csv(D / 'native_metrics.csv', metrics); save_csv(D / 'reductions.csv', reductions)
    save_csv(D / 'spatial_summary.csv', spatial); save_csv(D / 'spatial_seeds.csv', seed_metrics)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 5, 'pdf.fonttype': 42})
    fig = plt.figure(figsize=(3.45, 2.35), layout='constrained')
    fig.set_constrained_layout_pads(w_pad=.008, h_pad=.008, wspace=.025, hspace=.015)
    gs = fig.add_gridspec(5, 4, height_ratios=[.12, 1, .12, 1, .12])
    for row, method in [(0, 'cmi'), (2, 'openrcx_kernel')]:
        heading = fig.add_subplot(gs[row, :]); heading.set_axis_off()
        heading.text(.5, .5, LABELS[method] + ' − Full', ha='center', va='center', fontsize=6)
    for i, (title, bounds, edges, rowpanels) in enumerate(panels):
        gmax = max(float(np.max(abs(grid))) for grid, _ in rowpanels)
        unit = 10 ** math.floor(math.log10(gmax)); limit = math.ceil(gmax / unit) * unit
        for j, (grid, rec) in enumerate(rowpanels):
            ax = fig.add_subplot(gs[1 + 2*j, i])
            ax.set(xlim=(bounds[0], bounds[2]), ylim=(bounds[1], bounds[3]), aspect='equal')
            if j == 0: ax.set_title(title, pad=2, fontsize=5.1)
            ax.xaxis.set_major_locator(MaxNLocator(2)); ax.yaxis.set_major_locator(MaxNLocator(2))
            ax.tick_params(labelsize=4.3, pad=.8, length=1.5, labelbottom=(j == 1))
            ax.set_facecolor('#ededed')
            for spine in ax.spines.values(): spine.set_color('#9aa5af')
            im = ax.pcolormesh(*edges, grid, cmap='RdBu', norm=TwoSlopeNorm(0, -limit, limit), shading='flat', rasterized=True)
            ax.text(.02, .98, f"{rec['baseline_mae_ps']:.2f} → {rec['full_mae_ps']:.2f}", transform=ax.transAxes,
                    va='top', fontsize=4.3, bbox=dict(facecolor='white', alpha=.9, edgecolor='none', pad=.5))
        cax = fig.add_subplot(gs[4, i])
        cb = fig.colorbar(im, cax=cax, orientation='horizontal'); cb.set_ticks([-limit, 0, limit])
        cb.ax.tick_params(labelsize=4.3, pad=.8, length=1.5)
    fig.supxlabel(r'$x$ ($\mu$m); color scales in ps', fontsize=5.5)
    fig.supylabel(r'$y$ ($\mu$m)', fontsize=5.5)
    for ext in ('pdf', 'png'):
        fig.savefig(P / f'figures/downstream_two_kernels.{ext}', dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    report = dict(new_native_runs=48, reused_native_runs=96, golden_runs=8, common_support_episodes=498,
                  kernel_validation_max_scaled_error=validation['max_scaled_error'],
                  baseline_wins={m: {field: sum(r['baseline'] == m and r[field + '_reduction_pct'] is not None
                                    and r[field + '_reduction_pct'] > 0 for r in reductions)
                                    for field in ('net_cap_nrmse', 'ws_abs_ns', 'tns_abs_ns')} for m in METHODS[:2]},
                  spatial=spatial, spatial_seed_wins={m: sum(r['baseline'] == m and r['reduction_pct'] > 0 for r in seed_metrics) for m in METHODS[:2]},
                  layout='single column; MLI-ext./OpenRCX rows, four process columns; common scale within each column',
                  scope='Same-support fixed-node completion and native extraction; not computeTable injection')
    (D / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
