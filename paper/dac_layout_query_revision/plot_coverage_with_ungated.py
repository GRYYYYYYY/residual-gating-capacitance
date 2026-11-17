"""Render formal Fig. 4 from verified five-method scores, without inference.
Run using the Python environment in experiments/dac_characterization_20261114/env.sh.
Ungated data/provenance: trials/fig4_ungated_20261116T230943/.
"""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PAPER = Path(__file__).resolve().parent
SCORES = PAPER / 'tables/coverage_with_ungated.csv'
METHODS = [
    ('mli_sparse', 'MLI + sparse extension', '#777777', 'v', '-'),
    ('openrcx_kernel', 'OpenRCX kernel', '#46816d', '^', '--'),
    ('residual', 'Ungated', '#9467bd', 'D', '-.'),
    ('binary', 'Binary', '#176394', 'o', '-'),
    ('full', 'Full', '#b34332', 's', '-'),
]
CONDITIONS = [
    ('inside', 'mcar', 'In/random'), ('inside', 'block', 'In/block'),
    ('outside', 'mcar', 'Out/random'), ('outside', 'block', 'Out/block'),
    ('outside', 'extrapolation', 'Boundary'),
]
DOMAINS = [('public', 'Public'), ('reference', 'FEM'), ('to_asap7', 'Transfer')]

def main():
    with SCORES.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 300 and all(r['population'] == 'common' for r in rows)
    plt.rcParams.update({'font.size': 8, 'font.family': 'DejaVu Sans',
                         'pdf.fonttype': 42, 'axes.spines.top': False,
                         'axes.spines.right': False})
    fig, axs = plt.subplots(3, 5, figsize=(7.1, 4.5), sharex=True)
    fig.subplots_adjust(left=.085, right=.99, bottom=.11, top=.88, wspace=.36, hspace=.42)
    for i, (domain, title) in enumerate(DOMAINS):
        for j, (regime, protocol, heading) in enumerate(CONDITIONS):
            ax = axs[i, j]
            for method, label, color, marker, style in METHODS:
                series = sorted((r for r in rows if r['domain'] == domain
                                 and r['method'] == method and r['regime'] == regime
                                 and r['protocol'] == protocol),
                                key=lambda r: float(r['requested_holdout']))
                assert [float(r['requested_holdout']) for r in series] == [.1, .3, .5, .7]
                ax.plot([100 * float(r['requested_holdout']) for r in series],
                        [float(r['macro_nrmse']) for r in series],
                        linestyle=style, marker=marker, color=color, label=label, lw=1, ms=3)
            ax.set_yscale('log')
            ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.tick_params(labelsize=8)
            ax.set_xticks([10, 30, 50, 70])
            ax.grid(alpha=.15)
            if i == 0:
                ax.set_title(heading, fontsize=8)
            if j == 0:
                ax.set_ylabel(title + ' NRMSE', fontsize=8)
    fig.legend(*axs[0, 0].get_legend_handles_labels(), loc='upper center', ncol=5,
               frameon=False, fontsize=7.5, columnspacing=1.1, handletextpad=.4)
    fig.text(.5, .015, 'Requested characterization holdout (%)', ha='center')
    for ext in ['pdf', 'png']:
        fig.savefig(PAPER / 'figures' / ('coverage_four_ratios.' + ext),
                    bbox_inches='tight', dpi=180)
    plt.close(fig)

if __name__ == '__main__':
    main()
