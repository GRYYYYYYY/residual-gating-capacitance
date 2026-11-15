"""Input identity and protocol metadata; independent of query accuracy."""
from common_runtime import *
def main():
    groups={};queries={}
    for kind in ['fem','native']:
        groups[kind]=[];queries[kind]=[]
        for t,qs in workloads(kind):
            assert len({tuple(q['coordinates']) for q in qs})==len(qs),(kind,t['table_id'],'duplicate geometry')
            assert not ({tuple(q['coordinates']) for q in qs}&set(map(tuple,t['coordinates']))),(kind,t['table_id'],'query equals supplied support')
            batches=[]
            for b in [32,1,8]:
                for j in range(0,len(qs),b):batches.append(dict(limit=b,start=j,union_geometries=len(set(map(tuple,t['coordinates']))|{tuple(q['coordinates']) for q in qs[j:j+b]})))
            groups[kind].append(dict(table_id=t['table_id'],support_count=len(t['coordinates']),support_sha256=hashlib.sha256(json.dumps([t['coordinates'],t['labels']],sort_keys=True).encode()).hexdigest(),material_regions=len(t.get('materials') or []),components=t['target_names'],units=t['units'],process=t['process_id'],family=t['family'],query_count=len(qs),conductor_count=len(qs[0]['spec']['rectangles_override']) if kind=='fem' else None,batches=batches))
            for q in qs:queries[kind].append({k:q[k] for k in ['query_id','geometry_hash','table_id','coordinates','occurrence_count','sampling_probability','design_counts']})
    write(O/'WORKLOADS.json',dict(groups=groups,queries=queries,source_inputs={str(p.relative_to(R)):sha(p) for p in [OLD/'reference_plan.json',OLD/'native_replay_plan.json',OLD/'predictions_fem.jsonl',OLD/'predictions_native.jsonl',R/'configs/paper_models.json']}))
    write(O/'PROTOCOL.json',dict(baseline_commit='175fe3877e3f20de87f8fcb701b8df115802edd6',seed=20261115,cpu_core_hour_budget=8,max_concurrent_benchmark_workers=1,threads=1,canonical='all S + geometry-hash-sorted Q chunks32; frozen 3-member ensembles',batch_limits=[32,1,8],warmups=3,timed_blocks=20,query_denominator='unique requested geometry configurations, never support tokens or output components',solver_passes=3,solver_rhs=1,native_flow_passes=3,native_flow_budget=8,native_flow_seed=11,fit='source-selected updates once per fixed S/context/member; no query labels',cache='weights + target-adapted pointwise models + native compute grid; no answers or Transformer support hidden states',selection='all methods and Q limits retained regardless of precision or speed',source_training='none in this continuation',new_physical_geometries=0,semantics='2D symmetric layout-parameterized template vs native-rule agreement, separately',native_kernel='source-validated finite C++ compute-table counterpart after resolved width/context, not linked OpenRCX getter',native_flow='release OpenROAD; fixed nodes; no dense node enrichment or online model replacement'))
if __name__=='__main__':main()
