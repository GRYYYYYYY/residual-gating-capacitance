"""Verify final-manuscript assets and recompute headline/control scores (stdlib only)."""
import gzip
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'experiments/paper_controls'
CELLS = ['inside/mcar', 'inside/block', 'outside/mcar', 'outside/block', 'outside/extrapolation']


def aggregate(path):
    pooled = {}
    with gzip.open(path, 'rt') as handle:
        for line in handle:
            r = json.loads(line)
            if r['segment'] == 'all' or r['ratio'] != .3:
                continue
            regime = 'outside' if r['segment'] == 'outside' else 'inside'
            key = (r['method'], str(r['training_seed']), regime, r['protocol'], r['mask_seed'], r['process_id'], r['family'])
            se, sy = pooled.setdefault(key, ([0.] * len(r['squared_error']), [0.] * len(r['squared_truth'])))
            for i, (e, y) in enumerate(zip(r['squared_error'], r['squared_truth'])):
                se[i] += e
                sy[i] += y
    masks = defaultdict(list)
    for key, (se, sy) in pooled.items():
        masks[key[:5]].extend(math.sqrt(e/y) for e, y in zip(se, sy) if y > 0)
    cells = defaultdict(list)
    for key, values in masks.items():
        if values:
            cells[key[:4]].append(sum(values)/len(values))
    return {(method, seed, regime+'/'+protocol): sum(v)/len(v)
            for (method, seed, regime, protocol), v in cells.items()}


def numbers(row):
    return [float(v) for v in re.findall(r'(?<![\w.])\d+\.\d+', row)]


def verify():
    manifest = json.loads((ROOT/'paper/manifest.json').read_text())
    for name, expected in manifest.items():
        assert hashlib.sha256((ROOT/'paper'/name).read_bytes()).hexdigest() == expected, name
    for name, expected in json.loads((EVIDENCE/'records_manifest.json').read_text()).items():
        assert hashlib.sha256((EVIDENCE/name).read_bytes()).hexdigest() == expected, name
    models = json.loads((ROOT/'configs/paper_models.json').read_text())
    assert set(models) == {'public', 'reference', 'to_asap7'}
    summary = json.loads((EVIDENCE/'comparison_summary.json').read_text())
    counts = defaultdict(int)
    headline = {}
    for domain in models:
        data = aggregate(EVIDENCE/'scores'/domain/'learned_confirmation.jsonl.gz')
        affine = aggregate(EVIDENCE/'scores'/domain/'affine_confirmation.jsonl.gz')
        baseline = aggregate(EVIDENCE/'scores'/domain/'baseline_confirmation.jsonl.gz')
        chosen = json.loads((EVIDENCE/'scores'/domain/'affine_selection.json').read_text())['selected']
        for method, values in summary[domain].items():
            if method in ('anchor', 'affine'):
                continue
            actual_method = 'full_replayed' if method == 'full' else method
            for cell in CELLS:
                assert math.isclose(data[actual_method, 'ensemble', cell], values[cell], abs_tol=1e-12), (domain, method, cell)
        cmi = 'cmi1d' if domain == 'public' else 'cmi2d'
        headline[domain] = {}
        for cell in CELLS:
            full = summary[domain]['full'][cell]
            assert math.isclose(affine[chosen, 'ensemble', cell], summary[domain]['affine'][cell], abs_tol=1e-12)
            competitors = {m: value for (m, seed, c), value in baseline.items() if c == cell and (not m.startswith('cmi') or m == cmi)}
            assert len(competitors) == 5, (domain, cell, competitors)
            counts['vs_cmi'] += full < competitors[cmi]
            counts['vs_best_numerical'] += full < min(competitors.values())
            for alternative in ['residual', 'binary', 'affine']:
                counts['vs_'+alternative] += full < summary[domain][alternative][cell]
            headline[domain][cell] = dict(ours=full, **competitors)
    assert dict(counts) == dict(vs_cmi=15, vs_best_numerical=14, vs_residual=14, vs_binary=13, vs_affine=13), dict(counts)
    # Check every rounded method entry in the two main prediction tables.
    methods = [('CMI', 'cmi'), ('OpenRCX-LI', 'openrcx_li'), ('PCHIP', 'pchip'), ('IDW', 'idw'), ('RBF-GP', 'gp'), ('\\textbf{Ours}', 'ours')]
    for filename, domains in [('main_completion.tex', ['public', 'reference']), ('main_transfer.tex', ['to_asap7'])]:
        lines = (ROOT/'paper/tables'/filename).read_text().splitlines()
        for label, method in methods:
            row = next(line for line in lines if line.startswith(label))
            expected = []
            for domain in domains:
                m = ('cmi1d' if domain == 'public' else 'cmi2d') if method == 'cmi' else method
                expected += [round(headline[domain][c][m], 4) for c in CELLS]
            assert numbers(row) == expected, (filename, label, numbers(row), expected)
    print(json.dumps(dict(status='passed', manuscript_assets=len(manifest), conditions=15, wins=dict(counts)), indent=2))


if __name__ == '__main__':
    verify()
