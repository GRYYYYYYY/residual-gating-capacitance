"""Adapter contract and cached-fit equivalence on all 71 physical queries."""
from common_runtime import *
from benchmark import Engine
from learning import tensor
import numpy as np,torch
def main():
    pin();torch.set_num_threads(1);start=stamp();e=Engine('fem');rows=[]
    for t,qs in workloads('fem'):
        e.prepare(t,qs);g,o,v,ix=e.union(t,qs)
        direct=np.maximum(np.mean([e.att.projected(m,sc,g,o,v,e.att_steps) for m,sc in e.att_members],axis=0),0)[ix]
        cached,_=e.predict('attentioncap_adapted',t,qs);ys=np.asarray(e.p.scales['targets'][t['family']]);err=float(np.max(abs(cached-direct)/ys));assert err<2e-6
        x,pr=e.att.features(g)
        for i,q in enumerate(qs):
            spec=q['spec'];meta=spec['metadata'];j=ix[i]
            assert np.array_equal(x[j,:-1,:4].numpy(),np.asarray(spec['rectangles_override'],dtype='float32'))
            assert meta['target_index']==0
            assert set(meta['lateral_indices']+meta['grounded_indices']+meta['diagonal_indices'])==set(range(1,len(spec['rectangles_override'])))
            assert pr[j,1,-1]==1 and float(x[j,-1,-2])==1
            # The feature adapter retains the complete CTF stack; the solver
            # truncates it at its explicit extent. Compare epsilon functions
            # inside the domain, including both sets of layer boundaries.
            edges=sorted(set([0.,spec['extent']]+[r['top'] for r in t['materials'] if 0<r['top']<spec['extent']]+[r[0] for r in spec['materials'] if 0<r[0]<spec['extent']]))
            for lo,hi in zip(edges[:-1],edges[1:]):
                z=(lo+hi)/2
                er_input=next((r['er'] for r in t['materials'] if r['bottom']<=z<r['top']),1.)
                er_solver=next(er for top,er in spec['materials'] if z<top)
                assert er_input==er_solver,(t['table_id'],z,er_input,er_solver)
        rows.append(dict(table_id=t['table_id'],queries=len(qs),support_count=len(o),adapt_steps=e.att_steps,source_scaled_error=err,passed=True,material_boundary_geometry_projection_verified=True))
    write(O/'attention_equivalence.json',dict(rows=rows,passed=True,scope='existing component-supervised AttentionCap adapter and source-selected 50-step adaptation; explicit outer-ground token, same material stack, frozen template rectangles; not a reproduction of original full-matrix supervision',**elapsed(start)))
if __name__=='__main__':main()
