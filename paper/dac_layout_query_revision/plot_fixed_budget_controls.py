"""Convert the archived manuscript Table II to three grouped-bar panels.

Uses precisely the displayed table values; no fitting or new measurements.
Binary/Ungated are retained in the archived source, excluded from this figure.
"""
from pathlib import Path
import csv
import hashlib
import json
import re

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, LogFormatterMathtext, NullFormatter

P = Path(__file__).resolve().parent
D = P / 'data/fixed_budget_bars'
SOURCE = D / 'source_table.tex'
BUDGETS = (4, 8, 16, 32, 64)
METHODS = ('CNP', 'Adapted AC', 'Full')
COLORS = ('#6a78a7', '#ce9e51', '#b34332')
HATCHES = ('//', '..', '')
records = []
for line in SOURCE.read_text().splitlines():
    fields = [s.strip() for s in line.removesuffix(r'\\').split('&')]
    if len(fields) != 7 or fields[0] not in ('Public', 'FEM', 'Transfer'):
        continue
    for budget, value in zip(BUDGETS, fields[2:]):
        assert value == '--' or re.fullmatch(r'\d+\.\d+', value)
        records.append(dict(domain=fields[0], method=fields[1], budget=budget,
                            nrmse=value if value != '--' else '', available=value != '--'))
assert len(records) == 75
lookup = {(r['domain'], r['method'], r['budget']): r for r in records}
selected = [r for r in records if r['method'] in METHODS
            and (r['domain'] != 'Public' or r['budget'] in (4, 8))]
assert len(selected) == 36 and sum(r['available'] for r in selected) == 34
with (D / 'plotted_values.csv').open('w') as f:
    w = csv.DictWriter(f, list(selected[0]), lineterminator='\n'); w.writeheader(); w.writerows(selected)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 6,
                     'axes.labelsize': 6, 'axes.titlesize': 6.5, 'pdf.fonttype': 42})
fig, axs = plt.subplots(1, 3, figsize=(3.45, 1.85), sharey=True)
fig.subplots_adjust(left=.14, right=.995, bottom=.22, top=.74, wspace=.15)
bar_count = 0
for ax, domain, title in zip(axs, ('Public', 'FEM', 'Transfer'),
                             ('(a) Public', '(b) FEM', '(c) Transfer')):
    budgets = (4, 8) if domain == 'Public' else BUDGETS
    x = np.arange(len(budgets), dtype=float)
    present = ('CNP', 'Full') if domain == 'Public' else METHODS
    width = .74 / len(present)
    for j, method in enumerate(present):
        rows = [lookup[domain, method, budget] for budget in budgets]
        assert all(r['available'] for r in rows)
        values = np.array([float(r['nrmse']) for r in rows])
        xpos = x + (j - (len(present) - 1) / 2) * width
        k = METHODS.index(method)
        bars = ax.bar(xpos, values - .01, bottom=.01, width=width * .94,
                      color=COLORS[k], hatch=HATCHES[k], edgecolor='#333333',
                      linewidth=.35, label=method, zorder=3)
        # A log axis has no zero; every bar starts at the visible 0.01 floor.
        np.testing.assert_allclose([p.get_y() + p.get_height() for p in bars], values, atol=1e-15, rtol=1e-14)
        bar_count += len(values)
    ax.set_yscale('log'); ax.set_ylim(.01, 12)
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(LogFormatterMathtext())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(x, [str(b) for b in budgets])
    ax.set_title(title, pad=4)
    ax.set_axisbelow(True); ax.grid(axis='y', which='major', color='#dddddd', linewidth=.6)
    ax.tick_params(axis='both', labelsize=5.5, pad=1.5, length=2)
    ax.spines[['top', 'right']].set_visible(False)
    if domain == 'Public':
        ax.text(.5, .93, 'AC unavailable', transform=ax.transAxes,
                ha='center', va='top', fontsize=5.5, color='#555555')
    if domain == 'Transfer':
        ax.annotate('6.8753', xy=(x[0], 6.8753), xytext=(0, 4),
                    textcoords='offset points', ha='center', fontsize=5.5)
axs[0].set_ylabel('Macro NRMSE (log scale)', labelpad=2)
fig.supxlabel('Observed geometries, $B$', fontsize=6, y=.025)
handles, labels = axs[1].get_legend_handles_labels()
fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(.55, 1.01),
           ncol=3, frameon=False, fontsize=6.2, handlelength=1.4, columnspacing=1.2)
for ext in ('pdf', 'png'):
    fig.savefig(P / f'figures/fixed_budget_controls.{ext}', dpi=300, bbox_inches='tight')
plt.close(fig)
assert bar_count == 34
(D / 'verification.json').write_text(json.dumps(dict(
    source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(), source_cells=75,
    plotted_bars=bar_count, omitted_methods=['Binary', 'Ungated'],
    unavailable=[{k: r[k] for k in ('domain', 'method', 'budget')} for r in selected if not r['available']],
    values='Exact four-decimal values of the archived manuscript table',
    layout='single column; one row, three panels; shared log y axis; visible baseline 0.01',
    new_experiments=False), indent=2) + '\n')
print('Verified 34 bars against the original table; two unavailable Public AC evaluations omitted.')
