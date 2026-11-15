"""Resident single-target P2 FEM, identical fine meshes/boundaries to references.
One RHS suffices by Maxwell reciprocity. No mesh, factor or answer reuse across
queries or repetitions. Full-matrix convergence certification is not repeated.
"""
import time
BOOT=(time.perf_counter(),time.process_time())
from common_runtime import *
import importlib.util,tempfile
import numpy as np
SOURCE=UP/'workspaces/pdkcap-v0/runs/reference_full_v2/fem_source_snapshot.py'
spec=importlib.util.spec_from_file_location('frozen_fem',SOURCE);f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
EXPECTED='c2bed71f374ed99cd5040f91104558c4e243cadad935cfd6c3ea1587a7eb7c68'
assert sha(SOURCE)==EXPECTED
pin();INIT=elapsed(BOOT)
def solve(spec,path):
    total=stamp();st={};z=stamp()
    kwargs={k:v for k,v in spec.items() if k not in ('kind','id','metadata','electrode_groups')}
    eps,names=f.wire_mesh(path,**kwargs);st['mesh']=elapsed(z);z=stamp()
    mesh=f.MeshTri.load(str(path));basis=f.Basis(mesh,f.ElementTriP2(),intorder=4)
    epsilon=np.zeros(mesh.nelements);coverage=np.zeros(mesh.nelements,int)
    for name,er in eps.items():
        idx=mesh.subdomains[name];epsilon[idx]=f.EPS0*er;coverage[idx]+=1
    assert np.all(coverage==1)
    @f.BilinearForm
    def electrostatic(u,v,w):return w.epsilon*f.dot(f.grad(u),f.grad(v))
    K=f.asm(electrostatic,basis,epsilon=epsilon[:,None]*np.ones_like(basis.dx))
    dofs={name:basis.get_dofs(name).all() for name in names+['ground']}
    fixed=np.concatenate(list(dofs.values()));assert len(np.unique(fixed))==len(fixed)
    free=np.setdiff1d(np.arange(basis.N),fixed);st['assembly']=elapsed(z);z=stamp()
    lu=f.splu(K[free][:,free].tocsc(),permc_spec='MMD_AT_PLUS_A',diag_pivot_thresh=0.,options={'SymmetricMode':True});st['factor']=elapsed(z);z=stamp()
    u=np.zeros(basis.N);meta=spec['metadata'];u[dofs[names[meta['target_index']]]]=1
    u[free]=lu.solve(-(K[free][:,fixed]@u[fixed]));st['rhs']=elapsed(z);z=stamp()
    reaction=K@u;column=np.array([reaction[dofs[name]].sum() for name in names])
    lateral=-column[meta['lateral_indices']].sum();ground=column.sum()-column[meta['grounded_indices']].sum();diagonal=-column[meta['diagonal_indices']].sum()
    pred=[lateral,ground,diagonal];st['projection']=elapsed(z)
    return dict(prediction=pred,column=column.tolist(),elements=int(mesh.nelements),dofs=int(basis.N),matrix_dimension=len(names),rhs_count=1,stages=st,**elapsed(total))
def main():
    (O/'solver_raw.jsonl').write_text('')
    qs=[q for q in read(OLD/'reference_plan.json')['queries'] if q['split']=='formal'];assert len(qs)==71
    rows=[];rng=np.random.default_rng(20261115);cold=[]
    for q in qs:
        for lev in ['coarse','fine','wide']:
            r=read(OLD/'reference_results'/q['query_id']/lev/'receipt.json');assert r['query_id']==q['query_id'] and r['level']==lev;cold.append(r)
    # One unreported warmup; three complete, randomly ordered resident passes.
    with tempfile.TemporaryDirectory(prefix='dac-runtime-fem-') as td:
        sp=read(OLD/'reference_results'/qs[0]['query_id']/'fine/spec.json');warm=solve(sp,Path(td)/'mesh.msh')
        for block in range(3):
            for idx in rng.permutation(len(qs)):
                q=qs[idx];d=OLD/'reference_results'/q['query_id']/'fine';sp=read(d/'spec.json');ref=read(d/'result.json');r=solve(sp,Path(td)/'mesh.msh')
                target=np.asarray(ref['matrix_F_per_m'])[0];scale=max(abs(target));err=float(np.max(abs(np.array(r['column'])-target))/scale)
                assert err<1e-8,(q['query_id'],err)
                row=dict(query_id=q['query_id'],block=block,spec_sha256=sha(d/'spec.json'),column_scaled_error=err,**r);rows.append(row)
                with (O/'solver_raw.jsonl').open('a') as out:out.write(json.dumps(row)+'\n')
            print('resident solver pass',block,len(rows),flush=True)
    cold_sum=lambda lev,k:sum(r[k] for r in cold if lev is None or r['level']==lev)
    write(O/'solver_task_match.json',dict(status='completed',formal_queries=len(qs),query_ids=[q['query_id'] for q in qs],source_sha256=EXPECTED,output='lateral, ground, diagonal (zero retained), F/m; one geometry is one query',rhs_count=1,original_rhs_count=sorted(set(r['matrix_dimension'] for r in rows)),initialization=INIT,warmup=warm,passes=3,reuse='resident imports only; meshes, matrices, factors and answers rebuilt per query',reference_identity='same frozen fine spec; column vs certified full-matrix target row, reciprocity validated',max_column_scaled_error=max(r['column_scaled_error'] for r in rows),cold_fine_wall_s=cold_sum('fine','wall_s'),cold_fine_cpu_s=cold_sum('fine','cpu_s'),cold_certification_wall_s=cold_sum(None,'wall_s'),cold_certification_cpu_s=cold_sum(None,'cpu_s'),resident_mean_total_wall_s=sum(r['wall_s'] for r in rows)/3,resident_mean_total_cpu_s=sum(r['cpu_s'] for r in rows)/3,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,worker_cost=elapsed(BOOT)))
    csvwrite(O/'solver_timing.csv',[dict(query_id=r['query_id'],block=r['block'],wall_s=r['wall_s'],cpu_s=r['cpu_s'],dofs=r['dofs'],elements=r['elements'],**{f'{stage}_{k}':v for stage,dd in r['stages'].items() for k,v in dd.items()}) for r in rows])
if __name__=='__main__':main()
