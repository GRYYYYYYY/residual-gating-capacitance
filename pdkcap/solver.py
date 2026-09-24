"""Bounded numerical profiling with immutable solver snapshot and per-case ledger."""
import argparse,collections,copy,json,os,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
from .common import write_json,file_hash


def diagnose(results):
    groups=collections.defaultdict(dict)
    for entry in results:
        if entry['status']=='completed':groups[entry['reference_id']][entry['level']]=entry['result']
    checks=[]
    for ref,levels in groups.items():
        c=dict(reference_id=ref,complete=all(k in levels for k in (('coarse','fine') if ref=='analytic-coax' else ('coarse','fine','wide'))))
        if not c['complete']:c['passed']=False;checks.append(c);continue
        fine=np.array(levels['fine']['matrix_F_per_m']);scale=np.linalg.norm(fine)
        c['mesh_relative']=float(np.linalg.norm(np.array(levels['coarse']['matrix_F_per_m'])-fine)/scale)
        c['boundary_relative']=float(np.linalg.norm(np.array(levels['wide']['matrix_F_per_m'])-fine)/scale) if 'wide' in levels else 0.
        c['max_flux_energy_relative']=max(v['diagnostics']['charge_energy_relative'] for v in levels.values())
        c['max_reciprocity_relative']=max(v['diagnostics']['reciprocity_relative'] for v in levels.values())
        c['analytic_relative_error']=levels['fine'].get('analytic_relative_error',0.)
        c['matrix_structure_passed']=all(v['diagnostics']['smallest_symmetric_eigenvalue_scaled']>=-1e-10 and
                v['diagnostics']['max_positive_offdiagonal_scaled']<=1e-10 and
                v['diagnostics']['min_ground_capacitance_scaled']>=-1e-10 for v in levels.values())
        # Matrix norm checks never imply all weak pairs reach the same relative accuracy.
        denom=np.maximum(np.abs(fine),scale*1e-6)
        c['max_entry_mesh_relative_with_floor']=float(np.max(np.abs(np.array(levels['coarse']['matrix_F_per_m'])-fine)/denom))
        c['passed']=all(c[k]<=.01 for k in ('mesh_relative','boundary_relative','max_flux_energy_relative','analytic_relative_error')) and c['max_reciprocity_relative']<=1e-8 and c['matrix_structure_passed']
        checks.append(c)
    return checks


def main():
    p=argparse.ArgumentParser();p.add_argument('--suite',type=Path,required=True);p.add_argument('--fem-source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--case-timeout',type=int,default=120);p.add_argument('--max-wall-seconds',type=int,default=900)
    p.add_argument('--reuse',nargs='*',type=Path,default=[])
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    snapshot=a.output/'fem_source_snapshot.py';shutil.copyfile(a.fem_source,snapshot)
    suite=json.loads(a.suite.read_text());entries=[];started=time.perf_counter();reused={}
    for old in a.reuse:
        if json.loads((old/'manifest.json').read_text())['source_sha256']!=file_hash(snapshot):raise ValueError('reuse solver source differs')
        for line in (old/'ledger.jsonl').read_text().splitlines():
            entry=json.loads(line)
            if entry['status']=='completed':reused[entry['id']]=(entry,old)
    write_json(a.output/'manifest.json',dict(suite=str(a.suite.resolve()),suite_sha256=file_hash(a.suite),source_sha256=file_hash(snapshot),
                case_timeout=a.case_timeout,max_wall_seconds=a.max_wall_seconds,purpose='small numerical feasibility and cost pilot'))
    for case in suite:
        if time.perf_counter()-started>=a.max_wall_seconds:break
        if case['id'] in reused:
            entry,old=reused[case['id']]
            if json.loads((old/case['id']/'spec.json').read_text())!=case['spec']:raise ValueError('reuse spec mismatch')
            reused_directory=a.output/case['id'];reused_directory.mkdir()
            write_json(reused_directory/'spec.json',case['spec']);write_json(reused_directory/'result.json',entry['result'])
            entry=dict(entry,reused_from=str(old.resolve()),charged_wall_seconds=0.)
            entries.append(entry)
            with (a.output/'ledger.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
            continue
        out=a.output/case['id'];out.mkdir();write_json(out/'spec.json',case['spec'])
        env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        t=time.perf_counter()
        try:
            with (out/'worker.log').open('w') as log:
                r=subprocess.run([sys.executable,'-m','pdkcap.solver_worker','--source',str(snapshot.resolve()),'--spec',str((out/'spec.json').resolve()),'--output',str(out.resolve())],
                    stdout=log,stderr=subprocess.STDOUT,env=env,timeout=min(a.case_timeout,max(1,a.max_wall_seconds-(time.perf_counter()-started))))
            status='completed' if r.returncode==0 else 'failed'
        except subprocess.TimeoutExpired:status='timeout'
        entry=dict(id=case['id'],reference_id=case['reference_id'],level=case['level'],status=status,charged_wall_seconds=time.perf_counter()-t)
        if status=='completed':entry['result']=json.loads((out/'result.json').read_text())
        entries.append(entry)
        with (a.output/'ledger.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
        print(case['id'],status,round(entry['charged_wall_seconds'],2),flush=True)
    checks=diagnose(entries)
    write_json(a.output/'summary.json',dict(requested=len(suite),attempted=len(entries),
        completed=sum(e['status']=='completed' for e in entries),checks=checks,
        all_requested_passed=len(entries)==len(suite) and all(e['status']=='completed' for e in entries) and all(c['passed'] for c in checks),
        charged_wall_seconds=sum(e['charged_wall_seconds'] for e in entries),
        measured_solver_cpu_seconds=sum(e.get('result',{}).get('cpu_seconds',0.) for e in entries),
        scope='center fixtures + analytic control; extremes/full grid NOT validated',bulk_training_allowed=False))

if __name__=='__main__':main()
