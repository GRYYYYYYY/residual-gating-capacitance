"""Read the frozen evidence and reproduce the main census, coverage and STA summaries."""
from collections import defaultdict
import csv
import gzip
import json
from math import sqrt, isclose
from pathlib import Path
from statistics import mean

root = Path(__file__).resolve().parents[2]
results = root / 'results'
ref = root / 'paper/dac_layout_query_revision'
def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))
def jsonlines(path):
    with gzip.open(path,'rt') as f:
        yield from map(json.loads,f)

manifest=list(jsonlines(results/'layout_offgrid_20261115/query_manifest.jsonl.gz'))
assert len({r['geometry_hash'] for r in manifest})==19562
types=defaultdict(int)
for r in manifest:
    types[r['query_class']]+=r['occurrence_count']
assert sorted(types.values())==[967755,1676892,2696515,4547424]
assert sum(r['occurrence_count'] for r in manifest if r['quantized_to_node'])==849663

methods=('full','binary','residual','openrcx_kernel','mli_sparse')
cells=defaultdict(dict)
for domain in ('public','reference','to_asap7'):
    bucket=defaultdict(lambda:[0.,0.])
    valid={r['SQ_hash'] for r in rows(results/f'pex_kernel_revision/coverage_inventory_{domain}.csv') if r['openrcx_applicable']=='True'}
    for path in (results/f'pex_kernel_revision/coverage_{domain}.jsonl.gz',ref/f'trials/fig4_ungated_20261116T230943/ungated_{domain}.jsonl.gz'):
        for r in jsonlines(path):
            if r['SQ_hash'] not in valid or r['method'] not in methods or r['segment'] in ('all','complete_cell'):continue
            region='outside' if r['segment']=='outside' else 'inside'
            if region=='inside' and r['protocol']=='extrapolation':continue
            for k,(err,truth) in enumerate(zip(r['squared_error'],r['squared_truth'])):
                key=(domain,region,r['protocol'],float(r['ratio']),r['method'],r['mask_seed'],r['process_id'],r['family'],k)
                bucket[key][0]+=err
                bucket[key][1]+=truth
    masks=defaultdict(list)
    for key,(err,truth) in bucket.items():
        if truth>0:masks[key[:6]].append(sqrt(err/truth))
    aggregates=defaultdict(list)
    for key,v in masks.items():aggregates[key[:5]].append(mean(v))
    for key,v in aggregates.items():cells[key[:4]][key[4]]=mean(v)
assert len(cells)==60
for r in rows(ref/'tables/coverage_with_ungated.csv'):
    if r['method'] in methods:
        values=cells[r['domain'],r['regime'],r['protocol'],float(r['requested_holdout'])]
        assert isclose(values[r['method']],float(r['macro_nrmse']),abs_tol=1e-13)
assert [sum(v[m]<min(v['openrcx_kernel'],v['mli_sparse']) for v in cells.values()) for m in methods[:3]]==[60,55,50]
assert [sum(v['full']<v[m] for v in cells.values()) for m in methods[1:3]]==[49,55]
for axis in [None,0,1,3]:
    for setting in sorted(set(k[axis] if axis!=None else 'all' for k in cells)):
        selected=[v for k,v in cells.items() if axis is None or k[axis]==setting]
        print(setting,len(selected),*[round(mean(v[m] for v in selected),5) for m in methods])
spatial=ref/'data/downstream_two_kernels'
for rec in json.loads((spatial/'verification.json').read_text())['spatial']:
    name=rec['case'].split('/')[0]+'_'+rec['baseline']+'_endpoint_seedmean.csv.gz'
    with gzip.open(spatial/name,'rt') as f: points=list(csv.DictReader(f))
    assert len({v['endpoint'] for v in points})==rec['endpoints']==len(points)
    base,full=[mean(float(v[k]) for v in points) for k in ('baseline_error_ps','full_error_ps')]
    assert isclose(100*(1-full/base),rec['reduction_pct'],abs_tol=1e-9)
native=rows(spatial/'native_metrics.csv')
for kernel in ('cmi','openrcx_kernel'):
    wins=[]
    for metric in ('net_cap_nrmse','ws_abs_ns','tns_abs_ns'):
        scores=defaultdict(list)
        for r in native:scores[r['case'],r['budget'],r['method']].append(float(r[metric]))
        wins.append(sum(mean(v)>mean(scores[case,budget,'full']) for (case,budget,arm),v in scores.items() if arm==kernel))
    assert wins==[16,16,13]
cost=rows(results/'runtime_accuracy_20261115/rule_preparation_summary.csv')
for r,expected in zip(cost,(.70,.67,.91)):
    assert round(sum(float(r[k]) for k in ('prediction_all_four_platforms_s','payload_write_s','export_all_four_platforms_s')),2)==expected
assert round(sum(float(cost[0][k]) for k in cost[0] if k.startswith('shared_')),2)==.88
print('Raw coverage, census, endpoint matching summaries and export costs verified.')


audit_dir = results / 'dac_main13_integrated_revision/main13_20261117'
mli = json.loads((audit_dir / 'mli_status_reconciliation.json').read_text())
assert mli['archived_complete'] - mli['replayed_complete'] == 120
assert (mli['replayed_complete'], mli['all_queries']) == (35362, 171315)

def check_extraction_ratios(directory, expected_runs, expected_range):
    timings = rows(directory / 'native_flow_timing.csv')
    assert len(timings) == expected_runs
    by_arm = defaultdict(list)
    for run in timings:
        by_arm[run['case'], run['method']].append(float(run['extraction_s']))
    ratios = []
    for (case, arm), samples in by_arm.items():
        assert len(samples) == 3
        if arm == 'full':
            ratios.append(mean(samples) / mean(by_arm[case, 'original']))
    assert len(ratios) == 8
    assert (round(min(ratios), 3), round(max(ratios), 3)) == expected_range

check_extraction_ratios(results / 'runtime_accuracy_20261115', 96, (.983, 1.047))
check_extraction_ratios(results / 'pex_kernel_revision', 120, (.991, 1.035))
print('Full extraction-time ranges verified from 216 release runs across two protocols.')
