"""Build process-wise, transfer, missingness, and runtime result tables.

Every table here reads the same recorded runs as ``build_tables.py`` and adds
no new experiment except ``runtime_platform``, which re-times the existing
benchmark episode set with a per-platform breakdown.  The tables are:

``mode_stats.tex``      per-process x coupling-mode error statistics, in the
                        ``count:value`` layout of the parent study's TABLE VI.
``transfer_merged.tex`` the two transfer cohorts merged into one two-panel
                        table, in the column-group layout of TABLE II.
``mask_sweep_1d.tex``   the full missingness surface the mask sentence in the
``mask_sweep_transfer.tex``
                        protocol section refers to, split over two floats.
``runtime_platform.tex``per-platform latency, detailed header.
``runtime_summary.tex`` the same measurement summarised for the main text.

Run:  python build_tables_v3.py [--skip-runtime]
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from unified.aggregate import (add_records, condition_index, mask_macro_nrmse,  # noqa: E402
                               accumulator_payload, stream_records)
from unified.regime import regroup  # noqa: E402

import build_tables as bt  # noqa: E402

TABLES = HERE / 'tables'
TABLES.mkdir(exist_ok=True)

#: Coupling modes, in the order the parent study's TABLE VI reports them.
FAMILIES = ('OVER', 'UNDER', 'OVERUNDER', 'DIAGUNDER')
#: Processes of the public rule set, in the order the inventory lists them.
PROCESSES = ('asap7', 'gf180', 'ihp_sg13g2', 'sky130')
FAMILY_LABEL = {'OVER': 'OVER', 'UNDER': 'UNDER', 'OVERUNDER': 'OVERUNDER',
                'DIAGUNDER': 'DIAGUNDER'}
PROCESS_LABEL = {'asap7': 'asap7', 'gf180': 'gf180', 'ihp_sg13g2': 'ihp\\_sg13g2',
                 'sky130': 'sky130'}


#: Which runs each emitted table reads, so any number in it can be re-derived
#: without rerunning an experiment.  Written to ``generated_sources_v3.json``.
SOURCES = {}


def write(name, text, note=''):
    (TABLES / name).write_text('\\small\n' + text + '\n')
    print(f'  wrote tables/{name}{(" -- " + note) if note else ""}')


def source(name, **fields):
    SOURCES[name] = fields


def tex(name):
    """Escape the one character of a run key that is not literal in LaTeX.

    Process names are run identifiers -- ``ihp_sg13g2`` -- and an unescaped
    underscore is a subscript, so it has to be escaped wherever one is typeset.
    """
    return name.replace('_', r'\_')


def records(path):
    """Yield validated records of one run without building an accumulator.

    The statistics below are per instance, and an accumulator has already
    summed instances together, so this reads the record stream directly.
    """
    import gzip
    with gzip.open(ROOT / path, 'rt') as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


# --------------------------------------------------------------------------
# TABLE VI layout: process x coupling mode, best/worst/average/pooled
# --------------------------------------------------------------------------

#: Our deployed ensemble on the public confirmation cohort, and the anchor it
#: is a residual around, so the same table can be read for both.
OUR_RUN = 'runs/conf_public_holdout/records.jsonl.gz'
OUR_METHOD = 'sace_r_holdout'
ANCHOR_METHOD = 'sace_r_holdout_anchor'


def instance_rows(path, method, protocol, ratio):
    """Per-(process, family, table, mask) instance errors, in `n`-weighted form.

    An *instance* is one table under one mask seed, which is the unit the
    parent study's TABLE VI calls a held-out point set.  Its RMSE is the pooled
    normalized root-mean-square error over that instance's scored queries.
    """
    cells = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))
    for row in records(path):
        if row['method'] != method:
            continue
        if row['protocol'] != protocol or abs(row['ratio'] - ratio) > 1e-9:
            continue
        cell = cells[(row['process_id'], row['family'])][(row['table_id'], row['mask_seed'])]
        cell[0] += sum(row['squared_error'])
        cell[1] += sum(row['squared_truth'])
        cell[2] += row['n']
    return cells


def mode_stats_table(path=OUR_RUN, method=OUR_METHOD, protocol='block', ratio=.3,
                     name='mode_stats.tex'):
    """Public rules, process x coupling mode, four statistics per cell.

    ``best``/``worst`` are the best and worst single scored table, ``average``
    is the mean over tables of the per-table RMSE and ``pooled`` weights every
    scored query equally.  Following the parent table, the count in a
    best/worst cell is the number of instances attaining that value and the
    count in an average/pooled cell is the number of scored queries; counts
    therefore repeat across the four statistics and are not independent
    observations.  A cell with no positive truth energy is absent, not zero.
    """
    cells = instance_rows(path, method, protocol, ratio)
    body = [r'\begin{tabular}{llrrrr}\toprule',
            r'Process & Statistic & OVER & UNDER & OVERUNDER & DIAGUNDER \\\midrule']
    for process in PROCESSES:
        stats = {key: [] for key in ('best', 'worst', 'average', 'pooled')}
        for family in FAMILIES:
            instances = cells.get((process, family), {})
            errors = sorted(math.sqrt(se / sy) for se, sy, _ in instances.values() if sy > 0)
            points = sum(n for _, sy, n in instances.values() if sy > 0)
            pooled_se = sum(se for se, sy, _ in instances.values() if sy > 0)
            pooled_sy = sum(sy for se, sy, _ in instances.values() if sy > 0)
            if not errors:
                for key in stats:
                    stats[key].append(None)
                continue
            stats['best'].append((sum(1 for e in errors if e == errors[0]), errors[0]))
            stats['worst'].append((sum(1 for e in errors if e == errors[-1]), errors[-1]))
            stats['average'].append((points, sum(errors) / len(errors)))
            stats['pooled'].append((points, math.sqrt(pooled_se / pooled_sy)))
        if all(value is None for value in stats['pooled']):
            continue
        for key in ('best', 'worst', 'average', 'pooled'):
            row = []
            for entry in stats[key]:
                if entry is None:
                    row.append('--')
                elif entry[1] == 0:
                    row.append(f'{entry[0]}:0')
                else:
                    row.append(f'{entry[0]}:{entry[1]:.4f}')
            body.append(f'{PROCESS_LABEL[process]} & {key} & ' + ' & '.join(row) + r' \\')
        body.append(r'\addlinespace')
    if body[-1] == r'\addlinespace':
        body.pop()
    body.append(r'\bottomrule\end{tabular}')
    source(name, run=path, method=method, protocol=protocol, ratio=ratio,
           statistics='best/worst/average/pooled over scored tables and queries',
           note='per-instance RMSE read from the record stream, not the accumulator')
    write(name, '\n'.join(body), f'{protocol} {ratio:.0%}, {len(cells)} cells')


# --------------------------------------------------------------------------
# TABLE II layout: the two transfer cohorts merged into one table
# --------------------------------------------------------------------------

#: Display label of our method, which is what both cohorts' tables bold.
OURS_LABEL = 'Residual gating (ours)'


def label_of(domain):
    return {'to_asap7': 'To ASAP7', 'to_freepdk15': 'To FreePDK15'}[domain]


def merged_transfer_table(name='transfer_merged.tex'):
    """Transfer to both targets in one table, two column groups per panel.

    The two cohorts are the same protocol on the same kind of target, so the
    requested layout puts them side by side instead of in two tables that share
    a caption.  Rows are the union of both cohorts' methods; a method absent
    from one cohort keeps its row and shows the other cohort's cells.
    """
    domains = ('to_asap7', 'to_freepdk15')
    groups = [label_of(domain) for domain in domains]
    panels = {}
    for domain in domains:
        regrouped = bt.indexed(bt.cohort_accumulators(domain, 'confirmation'))
        method = bt.COHORTS[domain]['confirmation'][3]
        applicable = bt.APPLICABLE[bt.RANK[domain]]
        entries = [(n, l) for n, l in bt.BASELINES if not n.startswith('cmi') or n == applicable]
        entries += [('el_anchor', 'Anchor (ours)'), (method, OURS_LABEL)]
        for regime in ('inside', 'outside'):
            rows = {}
            for tag, label in entries:
                scores = [bt.score_of(regrouped, tag, regime, protocol, .3)
                          for protocol, _ in bt.PROTOCOLS]
                if all(value is None for value in scores):
                    continue
                rows[label] = scores
            panels[(domain, regime)] = (label_of(domain), method, rows)

    # One row set for both cohorts: a method listed in either is listed, so the
    # two column groups can be read across.
    ordered = []
    for _, _, rows in panels.values():
        for label in rows:
            if label not in ordered:
                ordered.append(label)

    def rank(label):
        values = [v for (_, _, rows) in panels.values() for v in rows.get(label, []) if v is not None]
        return sum(values) / len(values) if values else float('inf')

    ours = OURS_LABEL
    body = [r'\begin{tabular}{lrrrrrr}\toprule',
            r'&\multicolumn{3}{c}{' + groups[0] + r'}&\multicolumn{3}{c}{' + groups[1] + r'} \\',
            r'\cmidrule(lr){2-4}\cmidrule(lr){5-7}',
            r'Method&Random&Block&Extrap.&Random&Block&Extrap. \\']
    for index, (panel, regime_label) in enumerate((('inside', r'\emph{in-table}'),
                                                   ('outside', r'\emph{out-of-table}'))):
        body.append((r'\midrule' if index else '')
                    + r'\multicolumn{7}{c}{' + regime_label + r'} \\\midrule')
        labels = sorted((l for l in ordered if l != ours), key=rank)
        labels += [l for l in ordered if l == ours]
        for label in labels:
            cells = []
            for domain in ('to_asap7', 'to_freepdk15'):
                entry = panels.get((domain, panel))
                scores = entry[2].get(label) if entry else None
                for value in (scores or [None, None, None]):
                    cells.append(bt.cell(value))
            name_ = r'\textbf{' + label + r'}' if label == ours else label
            body.append(f'{name_} & ' + ' & '.join(cells) + r' \\')
    body.append(r'\bottomrule\end{tabular}')
    source(name, cohorts={domain: dict(baselines=bt.COHORTS[domain]['confirmation'][1],
                                       unified=bt.COHORTS[domain]['confirmation'][2],
                                       method=bt.COHORTS[domain]['confirmation'][3])
                          for domain in domains},
           note='the two transfer cohorts merged; same accumulators as build_tables.regimes')
    write(name, '\n'.join(body), f'{len(ordered)} methods x 2 cohorts')


# --------------------------------------------------------------------------
# The missingness surface behind the protocol sentence
# --------------------------------------------------------------------------

COHORT_OF = {
    'Public rules': ('public', 'confirmation'),
    '2-D reference': ('reference', 'confirmation'),
    'To ASAP7': ('to_asap7', 'confirmation'),
    'To FreePDK15': ('to_freepdk15', 'confirmation'),
}


#: The surface is split across two floats because all eight panels together run
#: about a third of a page past the text block.
SWEEP_GROUPS = (('mask_sweep_1d.tex', ('Public rules', '2-D reference')),
                ('mask_sweep_transfer.tex', ('To ASAP7', 'To FreePDK15')))


def mask_sweep_tables():
    """Every scored (protocol, missing rate) cell, ours against the rule.

    This is the data the protocol sentence summarises: three protocols at four
    missing rates, per cohort, with the applicable commercial multilinear rule
    beside our score so the gap can be read at every rate rather than only at
    the 30\\% the main tables use.
    """
    for name, labels in SWEEP_GROUPS:
        blocks = []
        for label in labels:
            domain, cohort = COHORT_OF[label]
            regrouped = bt.indexed(bt.cohort_accumulators(domain, cohort))
            method = bt.COHORTS[domain][cohort][3]
            applicable = bt.APPLICABLE[bt.RANK[domain]]
            for regime, regime_label in (('inside', 'in-table'), ('outside', 'out-of-table')):
                body = [r'\begin{tabular}{llrrrr}\toprule',
                        r'\multicolumn{6}{c}{' + f'{label}, {regime_label}' + r'} \\\midrule',
                        r'Protocol & Missing & '
                        + r' & '.join(f'{r:.0%}'.replace('%', r'\%') for r in bt.RATIOS)
                        + r' \\\midrule']
                for protocol, protocol_label in bt.PROTOCOLS:
                    for tag in (method, applicable):
                        scores = [bt.score_of(regrouped, tag, regime, protocol, ratio)
                                  for ratio in bt.RATIOS]
                        if all(value is None for value in scores):
                            continue
                        name_ = (r'\textbf{ours}' if tag == method
                                 else bt.NAMES.get(tag, tag))
                        lead = protocol_label if tag == method else ''
                        body.append(f'{lead} & {name_} & '
                                    + ' & '.join(bt.cell(value) for value in scores) + r' \\')
                    body.append(r'\addlinespace')
                if body[-1] == r'\addlinespace':
                    body.pop()
                body.append(r'\bottomrule\end{tabular}')
                blocks.append('\n'.join(body))
        source(name, cohorts={label: dict(baselines=bt.COHORTS[COHORT_OF[label][0]][COHORT_OF[label][1]][1],
                                          unified=bt.COHORTS[COHORT_OF[label][0]][COHORT_OF[label][1]][2],
                                          method=bt.COHORTS[COHORT_OF[label][0]][COHORT_OF[label][1]][3])
                              for label in labels},
               ratios=list(bt.RATIOS), protocols=[p for p, _ in bt.PROTOCOLS])
        write(name, '\n\n\\vspace{2pt}\n\n'.join(blocks), f'{len(blocks)} panels')


# --------------------------------------------------------------------------
# Latency, with the domain column split into platform and design
# --------------------------------------------------------------------------

#: Per-platform runs: the run, the table class (the `Design` half of the split
#: header), the commercial rule each platform is timed against, and the methods
#: that actually answer at that table rank.  A rule of the wrong rank returns
#: from its applicability guard, so timing it there measures the guard and not
#: the rule; those rows are dropped, as in the main-text timing table.
RUNTIME_RUNS = (
    ('benchmark_platform_public_v1', '13-node 1-D rules', 'cmi1d',
     ('cmi1d', 'openrcx_li', 'pchip', 'idw', 'gp', 'unified')),
    ('benchmark_platform_reference_v1', '128-node 2-D grids', 'cmi2d',
     ('cmi2d', 'openrcx_li', 'pchip', 'idw', 'gp', 'unified')),
)


def runtime_platform_table(name='runtime_platform.tex'):
    """Per-platform latency in the parent study's runtime header.

    Batch is one table's query set: the benchmark answers one episode at a time,
    so a batch is one table and its queries, and ``points/s`` counts the queries
    of that episode.  A batch column of one is kept so the header matches the
    table this format is taken from.
    """
    # The parent header carries a `Batch` column because its benchmark swept
    # batch sizes; this benchmark answers one table at a time, so batch is one
    # in every row and the column is dropped rather than printed constant.  The
    # remaining eight columns still need a smaller size and tighter columns to
    # fit the text block.
    body = [r'\setlength{\tabcolsep}{3pt}\scriptsize',
            r'\begin{tabular}{lllrrrrr}\toprule',
            r'Platform & Design & Method & Median batch ms & P95 batch ms & '
            r'Median ms/table & Tables/s & Points/s \\\midrule']
    for run, design, reference, applicable in RUNTIME_RUNS:
        path = ROOT / 'runs' / run / 'COMPLETED.json'
        if not path.exists():
            print(f'  {run} not run yet; skipping')
            return
        completed = json.loads(path.read_text())
        for platform, report in sorted(completed['report'].items()):
            names = sorted((n for n in report if n in applicable),
                           key=lambda n: report[n]['median_seconds'])
            for index, tag in enumerate(names):
                row = report[tag]
                median_ms = row['median_seconds'] * 1e3
                p95_ms = row['p95_seconds'] * 1e3
                tables_per_s = 1e3 / median_ms if median_ms > 0 else float('inf')
                points_per_s = row['mean_queries'] / row['median_seconds']
                label = (r'\textbf{Residual gating (ours)}' if tag == 'unified'
                         else bt.NAMES.get(tag, tag))
                lead_platform = tex(platform) if index == 0 else ''
                lead_design = design if index == 0 else ''
                body.append(f'{lead_platform} & {lead_design} & {label} & '
                            f'{median_ms:.3f} & {p95_ms:.3f} & {median_ms:.3f} & '
                            f'{tables_per_s:.1f} & {points_per_s:.0f} \\\\')
            body.append(r'\midrule')
    body[-1] = r'\bottomrule\end{tabular}'
    source(name, runs=[run for run, _, _, _ in RUNTIME_RUNS],
           note='measured in this session; see the drift check in the appendix prose')
    write(name, '\n'.join(body))


def runtime_summary_table(name='runtime_summary.tex'):
    """The cost claim on the platform axis: ours against the rule, per platform.

    This is the reading the detailed table is for.  It separates the two things
    that could set per-query cost -- the platform and the table class -- and
    shows that only the second one moves it.
    """
    body = [r'\begin{tabular}{llrrr}\toprule',
            r'Platform & Design & Method & ms/query & Relative to the rule \\\midrule']
    for run, design, reference, _ in RUNTIME_RUNS:
        path = ROOT / 'runs' / run / 'COMPLETED.json'
        if not path.exists():
            print(f'  {run} not run yet; skipping')
            return
        for platform, report in sorted(json.loads(path.read_text())['report'].items()):
            base = report[reference]['median_per_query_ms']
            for tag in (reference, 'unified'):
                row = report[tag]
                label = (r'\textbf{Residual gating (ours)}' if tag == 'unified'
                         else bt.NAMES.get(tag, tag))
                lead_platform = tex(platform) if tag == reference else ''
                lead_design = design if tag == reference else ''
                body.append(f'{lead_platform} & {lead_design} & {label} & '
                            f'{row["median_per_query_ms"]:.3f} & '
                            f'{row["median_per_query_ms"] / base:.2f}' + r'$\times$ \\')
            body.append(r'\midrule')
    body[-1] = r'\bottomrule\end{tabular}'
    source(name, runs=[run for run, _, _, _ in RUNTIME_RUNS])
    write(name, '\n'.join(body))


# --------------------------------------------------------------------------
# RC/STA downstream fidelity
# --------------------------------------------------------------------------

#: The re-extraction audit written by scripts/downstream_holdout_*.py.
DOWNSTREAM_RUN = 'downstream_holdout_v1'
PLATFORMS = ('asap7', 'gf180', 'ihp-sg13g2', 'sky130hs')
DESIGNS = ('aes', 'ibex')
MASKS = (.3, .5)
METHOD_ORDER = ('linear', 'anchor', 'ours')
METHOD_LABEL = {'linear': 'Linear', 'anchor': 'Anchor (ours)',
                'ours': 'Residual gating (ours)'}


def load_downstream():
    path = ROOT / 'runs' / DOWNSTREAM_RUN / 'summary.json'
    if not path.exists():
        print(f'  {path.name} absent; skipping the downstream tables')
        return None
    return json.loads(path.read_text())


def cell_of(data, platform, design, method, ratio):
    for cell in data['cells']:
        if (cell['platform'], cell['design'], cell['method']) == (platform, design, method) \
                and abs(cell['ratio'] - ratio) < 1e-9:
            return cell
    return None


def downstream_detail_table(name='downstream_detail.tex'):
    """The parent audit's downstream header, less its Group column.

    One row per scored cell: platform, design, method and mask, with the
    capacitance NRMSE against golden extraction and the largest absolute change
    in worst setup slack and in total negative slack over the three seeds.
    """
    data = load_downstream()
    if data is None:
        return
    # Seven columns of which four are identifiers: this is the widest table in
    # the paper and needs both a smaller size and tighter columns to fit.
    body = [r'\setlength{\tabcolsep}{3pt}\scriptsize',
            r'\begin{tabular}{lllrrrr}\toprule',
            r'Platform & Design & Method & Missing & Cap.\ NRMSE & '
            r'Max $|\Delta$WS| (ns) & Max $|\Delta$TNS| (ns) \\\midrule']
    for platform in PLATFORMS:
        for design in DESIGNS:
            for method in METHOD_ORDER:
                for ratio in MASKS:
                    cell = cell_of(data, platform, design, method, ratio)
                    if cell is None:
                        continue
                    label = METHOD_LABEL[method]
                    if method == 'ours':
                        label = r'\textbf{' + label + '}'
                    body.append(f'{tex(platform)} & {design} & {label} & {ratio:.0%}'.replace('%', r'\%') + ' & '
                                f'{cell["capacitance_nrmse_mean"]:.4f} & '
                                f'{cell["max_abs_ws_ns"]:.4g} & '
                                f'{cell["max_abs_tns_ns"]:.4g} \\\\')
            body.append(r'\addlinespace')
        body.append(r'\midrule')
    body[-1] = r'\bottomrule\end{tabular}'
    source(name, run=DOWNSTREAM_RUN,
           note='re-extraction audit on fixed golden routed layouts')
    write(name, '\n'.join(body))


def downstream_matrix_table(name='downstream_matrix.tex'):
    """One panel per platform in the parent TABLE XXIII layout.

    Rows are design x method x mask, which is the shape the parent study uses to
    report the same audit one process at a time.
    """
    data = load_downstream()
    if data is None:
        return
    blocks = []
    for platform in PLATFORMS:
        body = [r'\begin{tabular}{lllrrr}\toprule',
                r'\multicolumn{6}{c}{' + tex(platform) + r'} \\\midrule',
                r'Design & Method & Mask & Cap.\ NRMSE & '
                r'Max $|\Delta$WS| (ns) & Max $|\Delta$TNS| (ns) \\\midrule']
        for design in DESIGNS:
            for method in METHOD_ORDER:
                for ratio in MASKS:
                    cell = cell_of(data, platform, design, method, ratio)
                    if cell is None:
                        continue
                    label = METHOD_LABEL[method]
                    if method == 'ours':
                        label = r'\textbf{' + label + '}'
                    lead = design if (method == METHOD_ORDER[0] and ratio == MASKS[0]) else ''
                    body.append(f'{lead} & {label} & {ratio:.0%}'.replace('%', r'\%') + ' & '
                                f'{cell["capacitance_nrmse_mean"]:.4f} & '
                                f'{cell["max_abs_ws_ns"]:.4g} & '
                                f'{cell["max_abs_tns_ns"]:.4g} \\\\')
            body.append(r'\addlinespace')
        if body[-1] == r'\addlinespace':
            body.pop()
        body.append(r'\bottomrule\end{tabular}')
        blocks.append('\n'.join(body))
    # Four panels run past the text block, so they are emitted two at a time.
    for index in (0, 1):
        group = blocks[index * 2:(index + 1) * 2]
        if not group:
            continue
        piece = f'downstream_matrix_{index + 1}.tex'
        source(piece, run=DOWNSTREAM_RUN,
               platforms=list(PLATFORMS[index * 2:(index + 1) * 2]))
        write(piece, '\n\n\\vspace{2pt}\n\n'.join(group),
              f'{len(group)} platforms')


def downstream_summary_table(name='downstream_summary.tex'):
    """The same audit collapsed to one line per platform and method.

    NRMSE is the mean over the two designs and two masks; the timing columns are
    the largest deviation over every scored cell of that platform, which is the
    reading that answers whether better table completion moved the timing.
    """
    data = load_downstream()
    if data is None:
        return
    body = [r'\begin{tabular}{llrrr}\toprule',
            r'Platform & Method & Cap.\ NRMSE & Max $|\Delta$WS| (ns) & '
            r'Max $|\Delta$TNS| (ns) \\\midrule']
    for platform in PLATFORMS:
        for method in METHOD_ORDER:
            selected = [c for c in data['cells']
                        if c['platform'] == platform and c['method'] == method]
            if not selected:
                continue
            nrmse = sum(c['capacitance_nrmse_mean'] for c in selected) / len(selected)
            label = METHOD_LABEL[method]
            if method == 'ours':
                label = r'\textbf{' + label + '}'
            body.append(f'{tex(platform)} & {label} & {nrmse:.4f} & '
                        f'{max(c["max_abs_ws_ns"] for c in selected):.4g} & '
                        f'{max(c["max_abs_tns_ns"] for c in selected):.4g} \\\\')
        body.append(r'\addlinespace')
    if body[-1] == r'\addlinespace':
        body.pop()
    body.append(r'\bottomrule\end{tabular}')
    source(name, run=DOWNSTREAM_RUN, note='collapsed over designs and masks')
    write(name, '\n'.join(body))


def main():
    mode_stats_table()
    merged_transfer_table()
    mask_sweep_tables()
    if '--skip-runtime' not in sys.argv:
        runtime_platform_table()
        runtime_summary_table()
    downstream_detail_table()
    downstream_matrix_table()
    downstream_summary_table()
    (HERE / 'generated_sources_v3.json').write_text(json.dumps(SOURCES, indent=1) + '\n')
    print(f'  wrote generated_sources_v3.json ({len(SOURCES)} tables)')


if __name__ == '__main__':
    main()
