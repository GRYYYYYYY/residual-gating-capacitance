"""Generate the paper's LaTeX tables from recorded runs.

Every cell traces to a run directory under ``runs/``; the emitted
``generated_sources.json`` names them, so any number can be re-derived without
rerunning an experiment.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from unified.aggregate import (add_records, condition_index, load_accumulator,  # noqa: E402
                               mask_macro_nrmse, stream_records)
from unified.paired import bootstrap_delta, group_accumulator, prepare  # noqa: E402
from unified.regime import REGIMES, regroup  # noqa: E402
from unified.workspace import ARCHIVE  # noqa: E402

TABLES = HERE / 'tables'
TABLES.mkdir(exist_ok=True)

DOMAINS = ['public', 'reference', 'to_asap7', 'to_freepdk15']
#: domain -> cohort -> (frozen records run, baseline records run, our records run,
#: method tag, table label, table count).  ``frozen`` supplies only the queries
#: the baseline scorer cannot answer; it is not a comparison method.
COHORTS = {
    'public': {'confirmation': (None, 'bl3_public_conf',
                                'conf_public_holdout', 'sace_r_holdout', 'Public rules', 340)},
    'reference': {'confirmation': (None, 'bl3_reference_conf', 'conf_v10_reference', 'v10_all',
                                   'Reference', 16),
                  'boundary': (None, 'bl3_reference_bnd', 'bnd_v10_reference', 'v10_all',
                               'Reference boundary', 3)},
    'to_asap7': {'confirmation': (None, 'bl3_to_asap7_conf', 'conf_v10_to_asap7', 'v10_all',
                                  r'Transfer $\to$ ASAP7', 8),
                 'boundary': (None, 'bl3_to_asap7_bnd', 'bnd_v10_to_asap7', 'v10_all',
                              r'Transfer $\to$ ASAP7 edge', 2)},
    'to_freepdk15': {'confirmation': (None, 'bl3_to_freepdk15_conf', 'conf_v10_to_freepdk15',
                                      'v10_all', r'Transfer $\to$ FreePDK15', 8),
                     'boundary': (None, 'bl3_to_freepdk15_bnd', 'bnd_v10_to_freepdk15', 'v10_all',
                                  r'Transfer $\to$ FreePDK15 edge', 1)},
}
BASELINES = [('cmi1d', 'CMI-1D'), ('cmi2d', 'CMI-2D'), ('cmi4d', 'CMI-4D'),
             ('openrcx_li', 'OpenRCX-LI'), ('pchip', 'PCHIP'), ('idw', 'IDW'), ('gp', 'RBF-GP')]
PROTOCOLS = (('mcar', 'Random'), ('block', 'Block'), ('extrapolation', 'Extrap.'))
RATIOS = (0.1, 0.3, 0.5, 0.7)
NAMES = dict(BASELINES)
TIMING_RUN = 'benchmark_public_v3'
#: Independent axes of the tables in each domain.  A multilinear rule is only
#: defined on a table of matching rank, and an inapplicable rule answers with
#: the shared floor; showing that fallback as if it were the rule's own score
#: would misreport the baseline, so only the applicable variant is listed.
RANK = {'public': 1, 'reference': 2, 'to_asap7': 2, 'to_freepdk15': 2}
APPLICABLE = {1: 'cmi1d', 2: 'cmi2d', 4: 'cmi4d'}


def cell(value, digits=4):
    return '--' if value is None else f'{value:.{digits}f}'


def write(name, text):
    # Every generated table is typeset a size down: the widest has six columns
    # of eight-digit scores and would otherwise overflow the text block.
    (TABLES / name).write_text('\\small\n' + text + '\n')
    print(f'  wrote tables/{name}')


def load_cached(path, sources):
    """Cached accumulator when present, otherwise stream its sources."""
    cache = ROOT / 'runs/cache_v1' / (path.replace('/', '_') + '.json')
    if cache.exists():
        return load_accumulator(cache)
    if not sources or not all(source.exists() for source in sources):
        return None
    accumulator = stream_records(sources[0])
    for source in sources[1:]:
        add_records(accumulator, source)
    return accumulator


def cohort_accumulators(domain, cohort):
    """Baseline and candidate accumulators, kept separate.

    The mask-macro recipe is evaluated per (method, condition) cell, so a
    method's score is read from whichever accumulator holds its complete
    records; blending the two would sum unrelated methods into one another.
    """
    fixed, baselines, unified, _, _, _ = COHORTS[domain][cohort]
    frozen = load_cached(f'fz_{fixed}',
                         [ARCHIVE / 'runs' / fixed / 'records.jsonl.gz'] if fixed else [])
    baseline = load_cached(baselines, [ROOT / 'runs' / baselines / 'records.jsonl.gz'])
    neural = load_cached(unified, [ROOT / 'runs' / unified / 'records.jsonl.gz'])
    anchor_run = ELEMENT_RUNS.get(LABEL_OF.get((domain, cohort), ''))
    anchor = (load_cached(anchor_run, [ROOT / 'runs' / anchor_run / 'records.jsonl.gz'])
              if anchor_run else None)
    return [regroup(item) for item in (baseline, neural, frozen, anchor) if item is not None]


def indexed(regrouped):
    """Group name -> (regime accumulator, prebuilt condition index).

    ``mask_macro_nrmse`` rebuilds its condition index on every call, which is
    quadratic when a table asks for many methods and ratios; building it once
    per regime makes the sweep affordable.
    """
    built = {}
    for groups in regrouped:
        for name, group in groups.items():
            built.setdefault(name, []).append((group, condition_index(group)))
    return built


def score_of(regrouped, method, regime, protocol, ratio):
    """First defined value of a method across the accumulators that hold it."""
    for group, index in regrouped.get(regime, []):
        value = mask_macro_nrmse(group, method, protocol, ratio, index=index)
        if value is not None:
            return value
    return None


def regimes():
    sources = {'tables': {}}
    collected = {}
    for domain in DOMAINS:
        for cohort, spec in COHORTS[domain].items():
            _, _, _, method, _, _ = spec
            regrouped = cohort_accumulators(domain, cohort)
            if not regrouped:
                print(f'  skip {domain}/{cohort}: no records yet')
                continue
            regrouped = indexed(regrouped)
            for regime in ('inside', 'outside'):
                if regime not in regrouped:
                    continue
                rows = []
                applicable = APPLICABLE[RANK[domain]]
                entries = [(name, label) for name, label in BASELINES
                           if not name.startswith('cmi') or name == applicable]
                # The anchor is our own skip path, not a baseline: it is listed
                # so that the part of the network's out-of-table advantage that
                # comes from the boundary rule of its anchor is visible instead
                # of being attributed to the learned correction.
                for name, label in [*entries, ('el_anchor', 'Anchor (ours)'),
                                    (method, 'Residual gating (ours)')]:
                    scores = [score_of(regrouped, name, regime, protocol, .3)
                              for protocol, _ in PROTOCOLS]
                    if all(value is None for value in scores):
                        continue
                    rows.append(dict(method=name, label=label, scores=scores))
                shown = [row for row in rows if row['method'] == method]
                ordered = [row for row in rows if row['method'] != method]

                def rank(row):
                    defined = [v for v in row['scores'] if v is not None]
                    return sum(defined) / len(defined) if defined else float('inf')

                ordered.sort(key=rank)
                rows = ordered + shown
                collected[f'{domain}/{cohort}/{regime}'] = rows
                sweep = {f'{ratio:.1f}': {name: [score_of(regrouped, name, regime, protocol, ratio)
                                                 for protocol, _ in PROTOCOLS]
                                          for name in (method, applicable)}
                         for ratio in RATIOS}
                sources['tables'][f'{domain}/{cohort}/{regime}'] = dict(
                    label=spec[4], tables=spec[5], sweep=sweep, rows=rows,
                    frozen=spec[0], baselines=spec[1], unified=spec[2], method=method)
            (HERE / 'generated_sources.json').write_text(json.dumps(sources, indent=1) + '\n')

    for cohort_key in {(key.split('/')[0], key.split('/')[1]) for key in collected}:
        domain, cohort = cohort_key
        # One table per cohort with the two regimes as panels: the regimes are
        # the same comparison on the same population, and two half-empty tables
        # waste more space than they separate.
        # Each regime is also emitted on its own: the manuscript places the two
        # panels under separate captions, and deriving the splits here keeps them
        # from going stale when a cohort is re-scored.
        panels = {}
        for regime, heading in (('inside', r'\emph{in-table}'),
                                ('outside', r'\emph{out-of-table}')):
            rows = collected.get(f'{domain}/{cohort}/{regime}')
            if rows is None:
                continue
            panel = [r'Method & Random & Block & Extrap.\ \\\midrule']
            for row in rows:
                name = row['label']
                if row['method'] == COHORTS[domain][cohort][3]:
                    name = r'\textbf{' + name + '}'
                panel.append(f'{name} & ' + ' & '.join(cell(v) for v in row['scores']) + r' \\')
            panels[regime] = (heading, panel)
            write(f'{domain}_{cohort}_{regime}.tex',
                  '\n'.join([r'\begin{tabular}{lrrr}\toprule', *panel,
                             r'\bottomrule\end{tabular}']))
        body = [r'\begin{tabular}{lrrr}\toprule']
        for index, regime in enumerate(('inside', 'outside')):
            if regime not in panels:
                continue
            heading, panel = panels[regime]
            body.append((r'\midrule' if index else '')
                        + r'\multicolumn{4}{c}{' + heading + r'} \\\midrule')
            body += panel
        body.append(r'\bottomrule\end{tabular}')
        write(f'{domain}_{cohort}.tex', '\n'.join(body))
    print(f'  collected {len(collected)} regime panels in '
          f'{len({(key.split("/")[0], key.split("/")[1]) for key in collected})} tables')


def recorded_tables():
    """Ablation and schedule tables from the recorded run values."""
    data = json.loads((HERE / 'recorded.json').read_text())

    body = [r'\begin{tabular}{lrrr}\toprule',
            r'Training scheme & Random & Block & Extrap.\ \\\midrule']
    for row in data['ablations']['rows']:
        body.append(f"{row['name']} & " + ' & '.join(cell(v) for v in row['scores']) + r' \\')
    body += [r'\bottomrule\end{tabular}']
    write('ablations.tex', '\n'.join(body))

    body = [r'\begin{tabular}{lrrr}\toprule',
            r'Training budget & Random & Block & Extrap.\ \\\midrule']
    for row in data['schedule']['rows']:
        body.append(f"{row['name']} & " + ' & '.join(cell(v) for v in row['scores']) + r' \\')
    body += [r'\bottomrule\end{tabular}']
    write('schedule.tex', '\n'.join(body))

    body = [r'\begin{tabular}{lrr}\toprule',
            r'Anchor logit gap & Random & Block \\\midrule']
    for row in data['schedule']['transfer_gap']['rows']:
        body.append(f"{row['name']} & " + ' & '.join(cell(v) for v in row['scores'][:2]) + r' \\')
    body += [r'\bottomrule\end{tabular}']
    write('gap.tex', '\n'.join(body))


#: Gate and objective ablation on the public validation cohort.  Every row is
#: the same architecture, data, budget and seed set; the rows differ in the
#: gate's key and in what the objective averages over.
OBJECTIVE_ROWS = (
    ('input-independent keys, pointwise error', 'sace_r_v10_all',
     'runs/public_val_v10_all/records.jsonl.gz'),
    ('dictionary keys, pointwise error', 'rg2m', 'runs/val_rg2m_public/records.jsonl.gz'),
    ('dictionary keys, per-condition metric (ours)', 'rg2n',
     'runs/val_rg2n_public/records.jsonl.gz'),
)


def objective_table():
    accumulator = {}
    for _, _, path in OBJECTIVE_ROWS:
        if (ROOT / path).exists():
            add_records(accumulator, ROOT / path)
    if not accumulator:
        print('  objective ablation not scored yet')
        return
    grouped = regroup(accumulator)
    body = [r'\begin{tabular}{lrrr}\toprule',
            r'Gate key and objective & Random & Block & Extrap.\ \\\midrule']
    for label, method, _ in OBJECTIVE_ROWS:
        cells = []
        for regime, protocol in (('inside', 'mcar'), ('inside', 'block'),
                                 ('outside', 'extrapolation')):
            value = mask_macro_nrmse(grouped[regime], method, protocol, .3,
                                     index=condition_index(grouped[regime]))
            cells.append(value)
        if all(value is None for value in cells):
            continue
        name = r'\textbf{' + label + '}' if label.endswith('(ours)') else label
        body.append(f'{name} & ' + ' & '.join(cell(value) for value in cells) + r' \\')
    body.append(r'\bottomrule\end{tabular}')
    write('objective.tex', '\n'.join(body))


ELEMENT_RUNS = {
    'Reference': 'el2_conf_reference', 'ASAP7': 'el2_conf_to_asap7',
    'FreePDK15': 'el2_conf_to_freepdk15', 'Public rules': 'el2_conf_public'}
LABEL_OF = {('public', 'confirmation'): 'Public rules', ('reference', 'confirmation'): 'Reference',
            ('to_asap7', 'confirmation'): 'ASAP7', ('to_freepdk15', 'confirmation'): 'FreePDK15'}
ELEMENT_ROWS = (('Reference', 'outside', 'mcar'), ('Reference', 'inside', 'mcar'),
                ('ASAP7', 'outside', 'mcar'), ('ASAP7', 'inside', 'mcar'),
                ('FreePDK15', 'outside', 'mcar'), ('FreePDK15', 'inside', 'mcar'),
                ('Public rules', 'outside', 'mcar'), ('Public rules', 'inside', 'mcar'))
OURS_IN_ELEMENT = {'Reference': ('conf_v10_reference', 'v10_all'),
                   'ASAP7': ('conf_v10_to_asap7', 'v10_all'),
                   'FreePDK15': ('conf_v10_to_freepdk15', 'v10_all'),
                   'Public rules': ('conf_public_holdout', 'sace_r_holdout')}
ELEMENT_BEST = {'Reference': ('bl3_reference_conf', 'cmi2d'),
                'ASAP7': ('bl3_to_asap7_conf', 'cmi2d'),
                'FreePDK15': ('bl3_to_freepdk15_conf', 'cmi2d'),
                'Public rules': ('bl3_public_conf', 'cmi1d')}


def elements_table():
    """What the classical dictionary alone could have answered, per cell.

    The three columns are the score of the single best dictionary element, of a
    per-query arg-min over the applicable elements (which reads the label and is
    therefore a bound, not a method), and of the applicable commercial rule.  The
    last column is the trained network.  A cell where the bound is far below the
    baseline and the network is far above it is a gate that has not used what
    the dictionary offered.
    """
    body = [r'\begin{tabular}{llrrrr}\toprule',
            r'Cohort & Cell & Best element & Oracle & CMI & Ours \\\midrule']
    for cohort, regime, protocol in ELEMENT_ROWS:
        accumulator = {}
        add_records(accumulator, ROOT / 'runs' / ELEMENT_RUNS[cohort] / 'records.jsonl.gz')
        ours_run, ours_method = OURS_IN_ELEMENT[cohort]
        add_records(accumulator, ROOT / 'runs' / ours_run / 'records.jsonl.gz')
        base_run, base_method = ELEMENT_BEST[cohort]
        add_records(accumulator, ROOT / 'runs' / base_run / 'records.jsonl.gz')
        grouped = regroup(accumulator)[regime]
        index = condition_index(grouped)
        values = {name: mask_macro_nrmse(grouped, f'el_{name}', protocol, .3, index=index)
                  for name in [*dict(BASELINES).keys(), 'anchor', 'oracle']}
        defined = {name: value for name, value in values.items() if value is not None}
        single = {name: value for name, value in defined.items()
                  if name not in ('oracle', 'cmi1d', 'cmi2d', 'cmi4d')}
        best = min(single, key=lambda name: single[name])
        row = (f'{cohort} & {"out-of-table" if regime == "outside" else "in-table"} '
               f'{dict(PROTOCOLS)[protocol].lower()} & '
               f'{single[best]:.4f} ({NAMES.get(best, best)}) & {defined["oracle"]:.4f} & '
               f'{mask_macro_nrmse(grouped, base_method, protocol, .3, index=index):.4f} & '
               f'{mask_macro_nrmse(grouped, ours_method, protocol, .3, index=index):.4f}')
        body.append(row + r' \\')
    body.append(r'\bottomrule\end{tabular}')
    write('elements.tex', '\n'.join(body))


def timing_table():
    """Two panels, one per table rank, each against the CMI rule of that rank.

    A classical rule that is undefined at a table's rank returns immediately
    from its applicability guard, so timing it there measures the guard rather
    than the rule.  Only methods that actually answer are listed, and the
    reference column is the applicable commercial rule, because that is the
    comparison the cost claim is about.
    """
    body = [r'\begin{tabular}{llrrr}\toprule',
            r'Domain & Method & ms/episode & ms/query & relative to CMI \\\midrule']
    for domain, run, applicable, reference in (
            ('Public rules ($13$-node tables, $6$ queries)', 'benchmark_public_v4',
             ('cmi1d', 'idw', 'gp', 'unified'), 'cmi1d'),
            ('2-D reference ($128$-node tables, $64$ queries)', 'benchmark_reference_v4',
             ('cmi2d', 'openrcx_li', 'pchip', 'idw', 'gp', 'unified'), 'cmi2d')):
        path = ROOT / 'runs' / run / 'COMPLETED.json'
        if not path.exists():
            print(f'  {run} not run yet')
            continue
        report = json.loads(path.read_text())['report']
        base = report[reference]['median_per_query_ms']
        rows = sorted(((name, report[name]) for name in applicable),
                      key=lambda item: item[1]['median_seconds'])
        for index, (name, row) in enumerate(rows):
            label = r'\textbf{Residual gating (ours)}' if name == 'unified' else NAMES.get(name, name)
            cells = (f'{row["median_seconds"] * 1e3:.3f} & '
                     f'{row["median_per_query_ms"]:.3f} & '
                     f'{row["median_per_query_ms"] / base:.2f}' + r'$\times$')
            lead = domain if index == 0 else ''
            body.append(f'{lead} & {label} & {cells} \\\\')
        body.append(r'\midrule')
    body[-1] = r'\bottomrule\end{tabular}'
    write('timing.tex', '\n'.join(body))


#: The descriptor-key gate ablation: each cohort names the run that holds each
#: variant's records on that domain's *validation* cohort, which is the only
#: population a configuration decision may read.
KEY_VARIANTS = ('five-channel key, pointwise objective',
                'five-channel key, per-condition objective',
                'six-channel key, per-condition objective')
KEY_CELLS = (('inside', 'mcar'), ('inside', 'block'), ('outside', 'mcar'),
             ('outside', 'block'), ('outside', 'extrapolation'))
KEY_RUNS = {
    'to_freepdk15': {'five-channel key, pointwise objective': ('val_rg2n_to_freepdk15', 'rg2n'),
                     'five-channel key, per-condition objective': ('val_rg2m_to_freepdk15', 'rg2m'),
                     'six-channel key, per-condition objective': ('val_rg3_to_freepdk15', 'rg3'),
                     'reported gate': ('val_v10_to_freepdk15', 'v10_all')},
    'reference': {'five-channel key, pointwise objective': ('val_rg2n_reference', 'rg2n'),
                  'five-channel key, per-condition objective': ('val_rg2m_reference', 'rg2m'),
                  'reported gate': ('val_v10_reference', 'v10_all')},
    'to_asap7': {'five-channel key, pointwise objective': ('val_rg2n_to_asap7', 'rg2n'),
                 'five-channel key, per-condition objective': ('val_rg2m_to_asap7', 'rg2m'),
                 'six-channel key, per-condition objective': ('val_rg3_to_asap7', 'rg3'),
                 'reported gate': ('val_v10_to_asap7', 'v10_all')},
    'public': {'five-channel key, pointwise objective': ('val_rg2n_public', 'rg2n'),
               'five-channel key, per-condition objective': ('val_rg2m_public', 'rg2m'),
               'reported gate': ('val_holdout', 'sace_r_holdout')},
}
KEY_LABEL = {'to_freepdk15': 'FreePDK15', 'reference': '2-D reference',
             'to_asap7': 'ASAP7', 'public': 'public rules'}


def keyvariant_table():
    """Each gate variant against the reported gate, on the validation cohorts."""
    body = [r'\begin{tabular}{llrrrrr}\toprule',
            r'Gate & Cohort & \multicolumn{2}{c}{in-table} & '
            r'\multicolumn{3}{c}{out-of-table} \\',
            r'\cmidrule(lr){3-4}\cmidrule(lr){5-7}',
            r' & & Random & Block & Random & Block & Extrap.\ \\midrule']
    for cohort, runs in KEY_RUNS.items():
        accumulator = {}
        for run, _ in runs.values():
            add_records(accumulator, ROOT / 'runs' / run / 'records.jsonl.gz')
        grouped = regroup(accumulator)
        index = {regime: condition_index(grouped[regime]) for regime, _ in KEY_CELLS}
        table = {label: [mask_macro_nrmse(grouped[regime], tag, protocol, .3,
                                          index=index[regime])
                         for regime, protocol in KEY_CELLS]
                 for label, (_, tag) in runs.items()}
        baseline = table['reported gate']
        for label in [*KEY_VARIANTS, 'reported gate']:
            if label not in table:
                continue
            cells = []
            for position, value in enumerate(table[label]):
                if value is None:
                    cells.append('--')
                elif label != 'reported gate' and baseline[position] is not None \
                        and value < baseline[position]:
                    cells.append(r'\textbf{' + f'{value:.4f}' + '}')
                else:
                    cells.append(f'{value:.4f}')
            body.append(f'{label} & {KEY_LABEL[cohort]} & ' + ' & '.join(cells) + r' \\')
        body.append(r'\addlinespace')
    body[-1] = r'\bottomrule\end{tabular}'
    write('keyvariant.tex', '\n'.join(body))


def main():
    recorded_tables()
    timing_table()
    elements_table()
    objective_table()
    keyvariant_table()
    # Regime tables follow once every cohort's baselines have been scored.
    if '--regimes' in sys.argv:
        regimes()


if __name__ == '__main__':
    main()

