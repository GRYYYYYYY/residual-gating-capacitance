"""Regroup public capacitance curves, joining duplicate provenance before splitting."""
import argparse
import collections
import json
from pathlib import Path
from .common import FAMILIES, TARGETS, digest, file_hash, read_tables, write_json


def curve_content(r):
    # Ignore source/corner names in the duplicate fingerprint, retaining geometry.
    # Thus equal labels copied across corners cannot cross partitions.
    return digest({k: r[k] for k in ('process_id', 'family', 'metal', 'context_below',
                                    'context_above', 'width')} | {
        'rows': sorted([[row['spacing_left'], row['spacing_right'],
                         *[row[t] for t in TARGETS]] for row in r['rows']])})


def prepare(rows, seed=20260917):
    grouped = collections.defaultdict(list)
    for r in rows:
        if r['family'] in FAMILIES:
            key = tuple(r[k] for k in ('source_id', 'process_id', 'corner_id', 'family',
                                       'metal', 'context_below', 'context_above'))
            grouped[key].append(r)
    tables = []
    owners = collections.defaultdict(list)
    for key, curves in sorted(grouped.items()):
        source, process, corner, family, metal, below, above = key
        points = {}
        for r in curves:
            owners[curve_content(r)].append(len(tables))
            for row in r['rows']:
                x = (r['width'], row['spacing_left'], row['spacing_right'])
                y = tuple(row[t] for t in TARGETS)
                if x in points and tuple(points[x]) != y:
                    raise ValueError(f'Conflicting labels at identical coordinates: {key} {x}')
                points[x] = y
        xy = sorted(points.items())
        tables.append(dict(table_id=digest(key)[:24], domain='public_rules',
            source_id=source, process_id=process, corner_id=corner, family=family,
            metal=metal, context_below=below, context_above=above,
            coordinates=[list(x) for x, y in xy], labels=[list(y) for x, y in xy],
            target_names=list(TARGETS), units='source_rule_native_per_length',
            # Material values are NOT inferred from nominal process node.
            materials=None, source_table_ids=sorted(r['table_id'] for r in curves),
            curve_hashes=sorted(set(curve_content(r) for r in curves)),
            width_count=len({x[0] for x, y in xy})))
    parent = list(range(len(tables)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for ids in owners.values():
        for i in ids[1:]:
            parent[root(i)] = root(ids[0])
    components = collections.defaultdict(list)
    for i, t in enumerate(tables):
        components[root(i)].append(t)
    buckets = collections.defaultdict(list)
    for component in components.values():
        group_id = digest(sorted(t['table_id'] for t in component))[:24]
        for t in component:
            t['split_group'] = group_id
        strata = {(t['process_id'], t['family']) for t in component}
        assert len(strata) == 1
        buckets[next(iter(strata))].append((group_id, component))
    partition_counts = collections.Counter()
    for stratum, groups in sorted(buckets.items()):
        groups.sort(key=lambda item: digest([seed, item[0]]))
        n = len(groups)
        if n < 3:
            assignments = ['train'] * n  # no invented held-out examples
        else:
            nv = max(1, round(.15*n)); nt = max(1, round(.20*n))
            assignments = ['val']*nv + ['test']*nt + ['train']*(n-nv-nt)
        for (group_id, component), partition in zip(groups, assignments):
            for t in component:
                t['partition'] = partition
                partition_counts[partition] += 1
    # A separate process-transfer fold is derived without modifying the base split.
    audit = dict(raw_tables=len(rows), raw_capacitance_tables=sum(r['family'] in FAMILIES for r in rows),
                 regrouped_tables=len(tables), duplicate_components=len(components),
                 multiwidth_tables=sum(t['width_count'] > 1 for t in tables),
                 widths_histogram=dict(collections.Counter(t['width_count'] for t in tables)),
                 partitions=dict(partition_counts),
                 process_family_counts={f'{p}/{f}':sum(t['process_id']==p and t['family']==f for t in tables)
                                       for p,f in sorted(buckets)},
                 absent_materials=len(tables),
                 raw_family_counts=dict(collections.Counter(r['family'] for r in rows)))
    seen = {}
    for t in tables:
        for h in t['curve_hashes']:
            if h in seen and seen[h] != t['partition']:
                raise AssertionError('duplicate curve leakage')
            seen[h] = t['partition']
    audit['duplicate_curve_partition_overlap'] = 0
    return tables, audit


def main():
    p=argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); a=p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    tables,audit=prepare(read_tables(a.source))
    with (a.output/'tables.jsonl').open('x') as f:
        for t in tables: f.write(json.dumps(t, sort_keys=True)+'\n')
    audit.update(source=str(a.source.resolve()), source_sha256=file_hash(a.source),
                 output_sha256=file_hash(a.output/'tables.jsonl'), schema_version='pdkcap-0.1')
    write_json(a.output/'audit.json', audit)
    print(json.dumps(audit, indent=2))

if __name__=='__main__': main()
