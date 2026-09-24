"""Round3 bounded FEM runner; dynamic grid endpoints, original bulk runner unchanged."""
import argparse,concurrent.futures,copy,json,os,shutil,subprocess,sys,time,threading
from pathlib import Path
from .budget import authorization,Ledger
from .common import ROOT,file_hash,write_json
from .solver import diagnose


def cases(grid,phase):
    selected=[]
    ends={}
    for g in grid:
        e=ends.setdefault(g['reference_id'],[g['wi'],g['wi'],g['si'],g['si']])
        e[:]=[min(e[0],g['wi']),max(e[1],g['wi']),min(e[2],g['si']),max(e[3],g['si'])]
    for g in grid:
        a,b,c,d=ends[g['reference_id']]
        if phase=='extremes' and (g['wi'],g['si']) not in ((a,c),(a,d),(b,c),(b,d)):continue
        for level,hfactor,efactor in [('coarse',1.,1.),('fine',.5,1.),('wide',.5,2.)]:
            spec=copy.deepcopy(g['spec']);spec['h']*=hfactor;spec['extent']*=efactor;spec['materials'][-1][0]=spec['extent']
            selected.append(dict(id=g['id']+'-'+level,reference_id=g['id'],context_id=g['reference_id'],level=level,spec=spec))
    return selected


def main():
    p=argparse.ArgumentParser();p.add_argument('--grid',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fem-source',type=Path,required=True);p.add_argument('--phase',choices=['extremes','full'],required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--case-timeout',type=int,default=300)
    p.add_argument('--reuse',nargs='*',type=Path,default=[]);p.add_argument('--extreme-evidence',type=Path)
    p.add_argument('--factorization-equivalence',type=Path)
    p.add_argument('--max-new-cpu-hours',type=float,help='additional per-run cap, still charged to the shared ledger')
    a=p.parse_args();config,limit=authorization('solver')
    if not 1<=a.workers<=config['max_parallel_solver_workers']:raise ValueError('worker allocation exceeded')
    if a.phase=='full':
        if not a.extreme_evidence:raise PermissionError('extreme-grid validation must precede full scan')
        audit=json.loads(a.extreme_evidence.read_text())
        if audit.get('phase')!='extremes' or not audit.get('all_requested_passed'):raise PermissionError('extreme-grid gate did not pass')
        if audit['grid_sha256']!=file_hash(a.grid):raise PermissionError('extreme gate belongs to another grid')
    a.output.mkdir(parents=True,exist_ok=False);snapshot=a.output/'fem_source_snapshot.py';shutil.copyfile(a.fem_source,snapshot)
    worker_snapshot=a.output/'worker_snapshot.py';shutil.copyfile(ROOT/'pdkcap/solver_worker.py',worker_snapshot)
    solver_hash=file_hash(snapshot);ledger=Ledger(ROOT/'runs/compute_ledger.json',limit)
    planned=cases(json.loads(a.grid.read_text()),a.phase);reuse={}
    stage_lock=threading.Lock();stage_usage={'charged':0.,'reserved':0.}
    if a.max_new_cpu_hours is not None and a.max_new_cpu_hours<=0:raise ValueError('positive per-run cap required')
    for directory in a.reuse:
        manifest=json.loads((directory/'manifest.json').read_text())
        if manifest['source_sha256']!=solver_hash:
            if not a.factorization_equivalence:raise ValueError('reuse solver source differs')
            proof=json.loads(a.factorization_equivalence.read_text())
            old_text=(directory/'fem_source_snapshot.py').read_text()
            old_line="lu = splu(stiffness[free][:,free].tocsc())"
            new_line="lu = splu(stiffness[free][:,free].tocsc(), permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0., options={'SymmetricMode': True})"
            if not (proof['passed'] and proof['old_sha256']==manifest['source_sha256'] and proof['new_sha256']==solver_hash
                    and old_text.count(old_line)==1 and old_text.replace(old_line,new_line)==snapshot.read_text()
                    and proof['coarse_matrix_relative_difference']<1e-12):
                raise ValueError('reuse equivalence is not the verified factorization-only change')
        for line in (directory/'ledger.jsonl').read_text().splitlines():
            entry=json.loads(line)
            if entry['status']=='completed':reuse[entry['id']]=(entry,directory)
    write_json(a.output/'manifest.json',dict(phase=a.phase,grid_sha256=file_hash(a.grid),source_sha256=solver_hash,
        requested=len(planned),workers=a.workers,case_timeout=a.case_timeout,max_new_cpu_hours=a.max_new_cpu_hours,
        authorization_sha256=file_hash(ROOT/'configs/compute_authorization.json'),
        source_hashes={p.name:file_hash(p) for p in sorted((ROOT/'pdkcap').glob('*.py'))}))
    def worker(case):
        directory=a.output/case['id']
        if case['id'] in reuse:
            entry,source=reuse[case['id']]
            spec_source=source/case['id']/'spec.json'
            if not spec_source.exists() and entry.get('reused_from'):
                spec_source=Path(entry['reused_from'])/case['id']/'spec.json'
            if json.loads(spec_source.read_text())!=case['spec']:raise ValueError('reuse geometry differs')
            directory.mkdir();write_json(directory/'spec.json',case['spec'])
            write_json(directory/'result.json',entry['result'])
            write_json(directory/'REUSED.json',dict(source=str(source.resolve()),source_manifest_sha256=file_hash(source/'manifest.json'),
                factorization_equivalence_sha256=file_hash(a.factorization_equivalence) if a.factorization_equivalence else None))
            return dict(entry,reused_from=str(source.resolve()),charged_wall_seconds=0.)
        with stage_lock:
            if a.max_new_cpu_hours is not None and stage_usage['charged']+stage_usage['reserved']+a.case_timeout+10>a.max_new_cpu_hours*3600:
                raise RuntimeError('per-run CPU cap reached; stop dispatch without relaxing gates')
            stage_usage['reserved']+=a.case_timeout+10
        try:token=ledger.reserve(case['id'],a.case_timeout+10)
        except Exception:
            with stage_lock:stage_usage['reserved']-=a.case_timeout+10
            raise
        directory.mkdir();write_json(directory/'spec.json',case['spec']);start=time.perf_counter();status='failed'
        try:
            with (directory/'worker.log').open('w') as log:
                r=subprocess.run([sys.executable,str(worker_snapshot.resolve()),'--source',str(snapshot.resolve()),
                    '--spec',str((directory/'spec.json').resolve()),'--output',str(directory.resolve())],stdout=log,stderr=subprocess.STDOUT,
                    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'),timeout=a.case_timeout)
            status='completed' if r.returncode==0 else 'failed'
        except subprocess.TimeoutExpired:status='timeout'
        finally:
            elapsed=time.perf_counter()-start;ledger.close(token,elapsed,status)
            with stage_lock:
                stage_usage['reserved']-=a.case_timeout+10
                stage_usage['charged']+=elapsed
        entry=dict(id=case['id'],reference_id=case['reference_id'],context_id=case['context_id'],level=case['level'],status=status,charged_wall_seconds=elapsed)
        if status=='completed':entry['result']=json.loads((directory/'result.json').read_text())
        return entry
    entries=[];stopped=None
    # Only workers' worth of tasks in flight; never enqueue unbounded future work.
    iterator=iter(planned)
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        pending={}
        for _ in range(a.workers):
            try:c=next(iterator)
            except StopIteration:break
            pending[pool.submit(worker,c)]=c
        while pending:
            done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                case=pending.pop(future)
                try:entry=future.result()
                except Exception as exc:
                    stopped=f'{type(exc).__name__}: {exc}'
                    entry=dict(id=case['id'],reference_id=case['reference_id'],context_id=case['context_id'],level=case['level'],status='controller_failed',reason=stopped,charged_wall_seconds=0.)
                entries.append(entry)
                with (a.output/'ledger.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
                print(len(entries),len(planned),entry['id'],entry['status'],flush=True)
                if (a.output/'STOP_REQUESTED').exists():stopped='explicit graceful stop requested'
                if sum(e['status'] in ('failed','timeout') for e in entries)>=3:
                    stopped='three solver failures: pause dispatch for diagnosis'
                if not stopped:
                    try:c=next(iterator)
                    except StopIteration:continue
                    pending[pool.submit(worker,c)]=c
    checks=diagnose(entries)
    write_json(a.output/'summary.json',dict(phase=a.phase,grid_sha256=file_hash(a.grid),requested=len(planned),attempted=len(entries),checks=checks,
        completed=sum(e['status']=='completed' for e in entries),all_requested_passed=len(entries)==len(planned) and all(e['status']=='completed' for e in entries) and all(c['passed'] for c in checks),
        stopped_reason=stopped,charged_wall_seconds=sum(e['charged_wall_seconds'] for e in entries)))

if __name__=='__main__':main()
