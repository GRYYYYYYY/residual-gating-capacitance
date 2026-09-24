#!/usr/bin/env python3
"""Validate the complete 8-design x 13-rule audit before emitting final tables."""
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openrcbench.report import _bootstrap_ci

PLATFORMS = ('asap7', 'gf180', 'ihp-sg13g2', 'sky130hs')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def time_scale_ns(log):
    units = set()
    for line in log.read_text().splitlines():
        if not line.startswith('read_liberty '): continue
        path = Path(line.split()[-1])
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / 'tools/OpenROAD-flow-scripts/flow' / path
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as handle:
            header = handle.read(131072)
        match = re.search(r'time_unit\s*:\s*"?([0-9.eE+-]+)\s*(s|ms|us|ns|ps|fs)"?\s*;', header)
        if not match: raise ValueError(f'Missing Liberty time unit: {path}')
        units.add(float(match[1]) * dict(s=1e9,ms=1e6,us=1e3,ns=1,ps=1e-3,fs=1e-6)[match[2]])
    if len(units) != 1: raise ValueError(f'Nonuniform or missing Liberty time units: {log}')
    return units.pop()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('runs/downstream/comparisons'))
    parser.add_argument('--output-prefix',type=Path,default=Path('paper/iclr2027/generated/downstream'))
    args=parser.parse_args()
    rows, units, sources, routing_checks, raw_observations = [], {}, [], [], []
    for platform in PLATFORMS:
        for design in ('aes','ibex'):
            root=args.input/platform/design
            golden=json.loads((root/'golden.json').read_text())
            route_file=Path(__file__).resolve().parents[1]/'tools/OpenROAD-flow-scripts/flow/logs'/platform/design/'golden_20260909/5_2_route.json'
            routing=json.loads(route_file.read_text())
            drc_count=int(routing['detailedroute__route__drc_errors'])
            routing_checks.append(dict(platform=platform,design=design,drc_errors=drc_count,
                                       path=str(route_file),sha256=sha(route_file)))
            replay=json.loads((root/'golden_replay_check.json').read_text())
            if any(replay['metrics'][t]['rmse'] != 0 for t in ('capacitance','resistance')):
                raise ValueError('Golden replay differs from original routed design')
            factor=time_scale_ns(root/'golden.log')
            units[f'{platform}/{design}']=factor
            golden_ws=golden['timing_metrics']['finish__timing__setup__ws'] * factor
            golden_tns=golden['timing_metrics']['finish__timing__setup__tns'] * factor
            for name in ['golden']+[f'{m}_block{ratio}_seed{s}' for m in ['model','linear'] for ratio in [30,50] for s in range(3)]:
                path=root/f'{name}.json';v=json.loads(path.read_text())
                if v['spef_sha256'] != sha(v['spef']): raise ValueError(f'SPEF hash mismatch: {path}')
                for key in ['routed_database_sha256','constraints_sha256','openroad_sha256','timing_hook_sha256','num_cores','corner']:
                    if v['provenance'][key] != golden['provenance'][key]: raise ValueError((path,key))
                if not (v['comparison']['common_nets']==v['comparison']['golden_nets']==v['comparison']['candidate_nets']):
                    raise ValueError(f'Network sets differ: {path}')
                sources.append(dict(path=str(path),sha256=sha(path)))
            for method in ('model','linear'):
                for ratio in (30,50):
                    observations=[]
                    for seed in range(3):
                        v=json.loads((root/f'{method}_block{ratio}_seed{seed}.json').read_text())
                        if (v['variant']['method'], v['variant']['seed'],v['variant']['ratio']) != (method,seed,ratio/100):
                            raise ValueError('Variant identity mismatch')
                        o={f'{target}_{metric}':v['comparison']['metrics'][target][metric]
                           for target in ('capacitance','resistance') for metric in ('mae','rmse','nrmse','spearman')}
                        ws=v['timing_metrics']['finish__timing__setup__ws']*factor
                        tns=v['timing_metrics']['finish__timing__setup__tns']*factor
                        o.update(setup_worst_slack_ns=ws,setup_wns_ns=min(0,ws),setup_tns_ns=tns,
                                 setup_worst_slack_delta_ns=ws-golden_ws,
                                 setup_worst_slack_abs_error_ns=abs(ws-golden_ws),
                                 setup_wns_delta_ns=min(0,ws)-min(0,golden_ws),setup_tns_delta_ns=tns-golden_tns,
                                 setup_wns_abs_error_ns=abs(min(0,ws)-min(0,golden_ws)),
                                 setup_tns_abs_error_ns=abs(tns-golden_tns),
                                 extraction_seconds=v['extraction_seconds'],
                                 final_report_process_peak_mb=v['final_report_process_peak_kb']/1024)
                        if not all(math.isfinite(x) for x in o.values()): raise ValueError('Nonfinite downstream metric')
                        observations.append(o)
                        raw_observations.append(dict(platform=platform,design=design,method=method,
                                                     ratio=ratio/100,seed=seed,**o))
                    row=dict(platform=platform,design=design,method=method,ratio=ratio/100,seeds=3,
                             common_nets=golden['comparison']['common_nets'],golden_drc_errors=drc_count,
                             golden_wns_ns=min(0,golden_ws),golden_tns_ns=golden_tns)
                    for target, unit_key in [('capacitance','*C_UNIT'),('resistance','*R_UNIT')]:
                        row[target+'_unit']=json.dumps(golden['comparison']['units'].get(unit_key))
                    for key in observations[0]:
                        values=[o[key] for o in observations];mean=sum(values)/3
                        row[key+'_mean']=mean
                        row[key+'_std']=math.sqrt(sum((x-mean)**2 for x in values)/2)
                        if key.endswith(('_nrmse','_spearman')):
                            low,high=_bootstrap_ci(values,f'{platform}:{design}:{method}:{ratio}:{key}')
                            row[key+'_ci95_low']=low;row[key+'_ci95_high']=high
                    rows.append(row)
    assert len(rows)==32 and len(sources)==104
    timing_rows=[]
    for platform in PLATFORMS:
        for design in ('aes','ibex'):
            for method in ('model','linear'):
                selected=[o for o in raw_observations if (o['platform'],o['design'],o['method'])==(platform,design,method)]
                assert len(selected)==6
                timing_rows.append(dict(platform=platform,design=design,method=method,exports=6,
                    max_abs_worst_slack_delta_ns=max(o['setup_worst_slack_abs_error_ns'] for o in selected),
                    max_abs_wns_delta_ns=max(o['setup_wns_abs_error_ns'] for o in selected),
                    max_abs_tns_delta_ns=max(o['setup_tns_abs_error_ns'] for o in selected),
                    extraction_seconds_min=min(o['extraction_seconds'] for o in selected),
                    extraction_seconds_max=max(o['extraction_seconds'] for o in selected),
                    final_report_peak_mb_max=max(o['final_report_process_peak_mb'] for o in selected)))
    prefix=args.output_prefix;prefix.parent.mkdir(parents=True,exist_ok=True)
    prefix.with_suffix('.json').write_text(json.dumps(dict(rows=rows,source_results=sources,routing_checks=routing_checks,
        timing_rows=timing_rows,observations=raw_observations,
        liberty_time_unit_to_ns=units,memory_unit='MiB (KiB / 1024)',scope='test-table-only block masks on fixed golden routed layouts',
        runtime_scope='extraction wall time under shared CPU workload; peak RSS covers final-report process'),indent=2)+'\n')
    with prefix.with_suffix('.csv').open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines=['| Platform | Design | Method | Mask | Cap. NRMSE | Res. NRMSE |','|---|---|---|---:|---:|---:|']
    tex=[r'\begin{table}[t]',r'\centering',r'\small',
         r'\caption{Shared-layout downstream audit. Block masks affect only held-out test tables; NRMSE is mean $\pm$ standard deviation over three seeds.}',
         r'\label{tab:downstream}',r'\begin{tabular}{lllrrr}',r'\toprule',
         r'Platform & Design & Method & Mask & Cap. NRMSE & Res. NRMSE \\',r'\midrule']
    for r in rows:
        c=f"{r['capacitance_nrmse_mean']:.4f} ± {r['capacitance_nrmse_std']:.4f}"
        z=f"{r['resistance_nrmse_mean']:.4f} ± {r['resistance_nrmse_std']:.4f}"
        lines.append(f"| {r['platform']} | {r['design']} | {r['method']} | {r['ratio']:.0%} | {c} | {z} |")
        tex.append(' & '.join([r['platform'],r['design'],r['method'],str(int(r['ratio']*100))+r'\%',
                              c.replace('±',r'$\pm$'),z.replace('±',r'$\pm$')])+r' \\')
    tex += [r'\bottomrule',r'\end{tabular}',r'\end{table}']
    prefix.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    prefix.with_suffix('.tex').write_text('\n'.join(tex)+'\n')
    timing_prefix=prefix.with_name(prefix.name+'_timing')
    with timing_prefix.with_suffix('.csv').open('w') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(timing_rows[0]));writer.writeheader();writer.writerows(timing_rows)
    timing_tex=[r'\begin{table}[t]',r'\centering',r'\scriptsize',
        r'\caption{STA and observed resource use over six exports per method/design (two masks, three seeds). Timing columns are maximum absolute changes from golden in ns; WS is worst setup slack. Extraction wall time is a range under shared CPU load; peak RSS is the maximum for the whole final-report process.}',
        r'\label{tab:downstream-timing}',r'\begin{tabular}{lllrrrrr}',r'\toprule',
        r'Platform & Design & Method & $|\Delta\mathrm{WS}|$ & $|\Delta\mathrm{WNS}|$ & $|\Delta\mathrm{TNS}|$ & Extract. (s) & Peak (MiB) \\',r'\midrule']
    for r in timing_rows:
        timing_tex.append(' & '.join([r['platform'],r['design'],r['method'],
            f"{r['max_abs_worst_slack_delta_ns']:.4g}",
            f"{r['max_abs_wns_delta_ns']:.4g}",f"{r['max_abs_tns_delta_ns']:.4g}",
            f"{r['extraction_seconds_min']:.2f}--{r['extraction_seconds_max']:.2f}",
            f"{r['final_report_peak_mb_max']:.0f}"])+r' \\')
    timing_tex += [r'\bottomrule',r'\end{tabular}',r'\end{table}']
    timing_prefix.with_suffix('.tex').write_text('\n'.join(timing_tex)+'\n')
    print('Validated 104 result states; emitted 32 three-seed cells')

if __name__=='__main__': main()
