"""Census of logged native width/distance and fringe calls, before accuracy."""
import json,re,hashlib,csv,collections
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/layout_offgrid_20261115'
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
Ts=[json.loads(l) for l in (R/'runs/public_inventory_holdout_v1/tables.jsonl').read_text().splitlines()]
manifest=[];census=[];supports={};ambiguities=[]
for receipt in sorted((O/'native').glob('*/*/receipt.json')):
 rec=json.loads(receipt.read_text());case=rec['case'];proc,design=case.split('/');p=receipt.parent
 dbu=int(re.search(r'DAC_DBU (\d+)',(p/'native.log').read_text())[1]);factor=dbu/1000 if dbu>1000 else 1.;scale=1000*factor
 knots=collections.defaultdict(list);counts=collections.Counter()
 for line in (p/'trace.tsv').open():
  a=line.rstrip().split('\t')
  if a[0]=='K':knots[a[1]].append([int(a[3]),float(a[4]),float(a[5])])
  else:counts[tuple(a)]+=1
 match={}
 for a,n in counts.items():
  typ,ptr=a[:2];met,over,mou,w,we,s,se=map(int,a[2:9]);cc,fr=map(float,a[9:11])
  if (ptr,met,we) not in match:
   kk=knots.get(ptr,[]);finite=[k for k in kk if k[0]/scale<90]
   candidates=[]
   for t in Ts:
    if t['process_id']!={'ihp-sg13g2':'ihp_sg13g2','sky130hs':'sky130'}.get(proc,proc) or t['metal']!=met:continue
    x=np.array(t['coordinates']);y=np.array(t['labels'])
    if len(x)!=len(finite) or not len(x) or round(x[0,0]*scale)!=we:continue
    if np.array_equal(np.floor(x[:,1]*scale+.5).astype(int),np.array(finite)[:,0]) and np.allclose(y/factor,np.array(finite)[:,1:],rtol=1e-10,atol=1e-18):candidates.append(t)
   match[ptr,met,we]=candidates
  candidates=match[ptr,met,we]
  t=candidates[0] if len(candidates)==1 else None
  kk=knots.get(ptr,[]);finite=[k[0] for k in kk if k[0]/scale<90]
  sh=digest(kk);rule=t['table_id'] if t else 'unresolved-'+sh[:16]
  if t:supports[rule]=t
  finite_query=typ=='Q' and s>=0 and s/scale<90 and bool(finite)
  on=finite_query and w==we and s in finite
  # Native width map is rank one per selected table. Raw width mismatch is
  # separately outside the supported affine subspace, not bbox interpolation.
  clas=('on_grid' if on else 'off_grid_in_support' if w==we and min(finite)<=s<=max(finite) else 'off_grid_out_of_support') if finite_query else 'fringe_or_unsupported'
  eff='on_grid' if se in finite else 'off_grid' if finite_query and 0<=se/scale<90 else 'special'
  gh=digest([proc,rec['rules_sha256'],rule,met,mou,we,w,s,typ])
  row=dict(query_id=digest([case,gh,cc,fr])[:24],geometry_hash=gh,process=proc,corner='typ',design=design,rule_key=rule,layer=met,family=t['family'] if t else 'UNRESOLVED',context_below=t['context_below'] if t else None,context_above=t['context_above'] if t else None,raw_coordinates=[w/scale,s/scale,s/scale],native_effective_coordinates=[we/scale,se/scale,se/scale],raw_dbu=[w,s],effective_dbu=[we,se],dbu_per_um=dbu,coordinate_scale=scale,mapping_level='NATIVE_PATTERN_INSTANCE' if t else 'UNSUPPORTED',physical_reference_status='unmatched_material_and_component',query_class=clas,effective_query_class=eff,quantized_to_node=bool(finite_query and not on and eff=='on_grid'),off_affine_span=w!=we,S_hash=sh,material_hash=None,boundary_hash=None,component=['native_coupling','native_fringe'],unit='native_per_internal_length',occurrence_count=n,sampling_probability=1.,native_prediction=[cc,fr],checkpoint_or_binary_hash=rec['binary_sha256'],provenance=dict(trace=str((p/'trace.tsv').relative_to(R)),table_pointer=ptr,odb_sha256=rec['odb_sha256'],rules_sha256=rec['rules_sha256']),call_type=typ,support_count=len(finite),support_min=min(finite)/scale if finite else None,support_max=max(finite)/scale if finite else None,length_weight=None)
  manifest.append(row)
 groups=collections.defaultdict(list)
 for r in manifest:
  if r['process']==proc and r['design']==design:groups[(r['query_class'],r['family'],r['layer'])].append(r)
 for (cl,fam,layer),rr in groups.items():census.append(dict(process=proc,design=design,layer=layer,family=fam,query_class=cl,occurrences=sum(r['occurrence_count'] for r in rr),unique_geometries=len(set(r['geometry_hash'] for r in rr)),quantized_to_node=sum(r['occurrence_count'] for r in rr if r['quantized_to_node']),resolved=sum(r['occurrence_count'] for r in rr if r['mapping_level']!='UNSUPPORTED')))
 print(case,'calls',sum(counts.values()),'unique',len(counts),'matched',sum(len(x)==1 for x in match.values()),'tables',len(match),flush=True)
with (O/'query_manifest.jsonl').open('w') as f:
 for r in manifest:f.write(json.dumps(r)+'\n')
with (O/'query_census.csv').open('w') as f:w=csv.DictWriter(f,census[0],lineterminator='\n');w.writeheader();w.writerows(census)
(O/'native_supports.json').write_text(json.dumps(supports))
summary=dict(instrumented_scope='extDistWidthRCTable three-argument getRC and getFringeRC; excludes five-argument diagonal, getRC_99, last-width fringe, resistance and assembly',total_logged_calls=sum(r['occurrence_count'] for r in manifest),unique_geometries=len(set(r['geometry_hash'] for r in manifest)),classes={k:sum(r['occurrence_count'] for r in manifest if r['query_class']==k) for k in sorted(set(r['query_class'] for r in manifest))},quantized_to_node=sum(r['occurrence_count'] for r in manifest if r['quantized_to_node']),unresolved_calls=sum(r['occurrence_count'] for r in manifest if r['mapping_level']=='UNSUPPORTED'),physical_reference_matched_calls=0,layout_modified=False,all_original_characterization_samples_retained=True)
(O/'census_summary.json').write_text(json.dumps(summary,indent=2));print(summary)
