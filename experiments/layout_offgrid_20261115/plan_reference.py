"""Freeze layout-parameterized template cohort using geometry only.
No native/CTF physical equivalence is assumed. All original S nodes retained.
"""
import sys,json,hashlib,collections,copy
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from pdkcap.reference import parse_ctf,geometry
O=R/'results/layout_offgrid_20261115';C=R/'.cache/AttentionCap/pattern_gen/itf_lib/asap7.ctf'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
stack=parse_ctf(C);ts={t['table_id']:t for t in map(json.loads,(R/'runs/reference_dataset_v2/tables.jsonl').read_text().splitlines())}
records=[json.loads(l) for l in (O/'query_manifest.jsonl').read_text().splitlines()]
candidates={};reasons=collections.Counter()
for r in records:
 if r['process']!='asap7' or r['call_type']!='Q' or r['layer'] not in [4,5] or r['family'] not in ['OVER','UNDER','OVERUNDER']:continue
 layer=r['layer'];fam=r['family'];cid=f'asap7-M{layer}-{fam}';t=ts[cid]
 if (r['context_below'],r['context_above'])!=(t['context_below'],t['context_above']):reasons['nonadjacent_context']+=r['occurrence_count'];continue
 w,s,_=r['raw_coordinates'];metal=stack['metals'][layer-1]
 if not (metal['wmin']<=w<=4*metal['wmin'] and metal['smin']<=s<=16*metal['smin']):reasons['outside_template_range']+=r['occurrence_count'];continue
 x=[w,s,s];tol=.5/r['coordinate_scale']
 if np.any(np.max(abs(np.array(t['coordinates'])-x),axis=1)<=tol):reasons['original_ctf_node_at_dbu_resolution']+=r['occurrence_count'];continue
 spec=geometry(stack,layer-1,fam,w,s);spec['refine_conductor_indices']=[0,1,2]
 gh=hashlib.sha256(json.dumps([spec,stack['sha256']],sort_keys=True).encode()).hexdigest()
 if gh not in candidates:
  candidates[gh]=dict(query_id=gh[:24],geometry_hash=gh,table_id=cid,process='asap7',layer=layer,family=fam,coordinates=x,mapping_level='LAYOUT_PARAMETERIZED_TEMPLATE',query_class='off_grid_in_support',spec=spec,material_hash=stack['sha256'],boundary_hash=hashlib.sha256(json.dumps([spec['extent'],spec['materials'],spec['rectangles_override'][3:]],sort_keys=True).encode()).hexdigest(),occurrence_count=0,design_counts={},native_query_ids=[],S_hash=hashlib.sha256(json.dumps([t['coordinates'],t['labels']],sort_keys=True).encode()).hexdigest(),support_count=len(t['coordinates']),geometry_checks='positive dimensions, CTF wmin/smin, nonintersection checked by mesher; no new full DRC',projection='lateral=-C01-C02; ground=sum(C0j)-sum(C0,context); diagonal=0; F/m',transformation='native width/spacing; mirror equal-width side lines at equal gaps; finite grounded immediate context planes and external shield; native net identities and asymmetric surroundings not retained')
 q=candidates[gh];q['occurrence_count']+=r['occurrence_count'];q['design_counts'][r['design']]=q['design_counts'].get(r['design'],0)+r['occurrence_count'];q['native_query_ids'].append(r['query_id'])
groups=collections.defaultdict(list)
for q in candidates.values():groups[q['table_id']].append(q)
queries=[]
for cid,qs in sorted(groups.items()):
 qs.sort(key=lambda q:hashlib.sha256(('20261115'+q['geometry_hash']).encode()).hexdigest())
 # Small, fixed pilot per context; independent final cohort, no error-based selection.
 npilot=min(2,max(0,len(qs)//4));nfinal=min(12,len(qs)-npilot)
 for i,q in enumerate(qs[:npilot+nfinal]):
  q.update(split='pilot' if i<npilot else 'formal',sampling_probability=(npilot if i<npilot else nfinal)/len(qs),stratum_population=len(qs),sampling_order=i)
  queries.append(q)
plan=dict(seed=20261115,queries=queries,all_candidate_count=len(candidates),all_candidate_occurrences=sum(q['occurrence_count'] for q in candidates.values()),exclusion_occurrences=dict(reasons),native_physical_reference_matched=False,template_coordinate_source='unmodified native logged queries',solver_source='reference_full_v2/fem_source_snapshot.py',support_policy='all 153 original CTF-derived reference samples per context, hash-checked reuse',stage='frozen before direct query solves and method predictions')
if (O/'reference_plan.json').exists():
 old=json.loads((O/'reference_plan.json').read_text());assert old['queries']==plan['queries'], 'frozen geometry plan changed'
else:(O/'reference_plan.json').write_text(json.dumps(plan,indent=2))
(O/'template_coverage.json').write_text(json.dumps(dict(candidate_geometries=len(candidates),candidate_occurrences=plan['all_candidate_occurrences'],exclusions=dict(reasons)),indent=2))
print('candidates',len(candidates),'selected',len(queries),'by split',dict(collections.Counter(q['split'] for q in queries)), 'contexts',dict(collections.Counter(q['table_id'] for q in queries)))
