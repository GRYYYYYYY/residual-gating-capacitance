"""Shared FEM S/Q: specified MLI, pinned compute kernel, learned slot generation."""
from common import *
from kernels import *
import gzip,subprocess,importlib.util,collections
sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'));sys.modules.pop('common',None)
spec=importlib.util.spec_from_file_location('prior_predict',R/'experiments/dac_characterization_20261114/evaluate.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
from unified.queries import query_table

def cpp(x,y,q,override):
 ws=np.unique(x[:,0]);lines=['1',f'{len(ws)} {len(q)} {len(override)}']
 for w in ws:
  ids=np.flatnonzero(x[:,0]==w);ids=ids[np.argsort(x[ids,1])];lines.append(f'{round(w*1000)} {len(ids)}')
  for i in ids:lines.append(' '.join(map(str,[int(np.floor(x[i,1]*1000+.5)),*y[i]])))
 for (j,slot),v in sorted(override.items()):lines.append(' '.join(map(str,[j,slot,*v])))
 for a in q:lines.append(f'{int(np.floor(a[0]*1000+.5))} {int(np.floor(a[1]*1000+.5))}')
 text='\n'.join(lines)+'\n';p=subprocess.run([str(O/'pinned_kernel')],input=text,text=True,capture_output=True,check=True)
 return np.array([[float(v) for v in l.split()] for l in p.stdout.splitlines()]),text

def main():
 pin();start=stamp();ts={t['table_id']:t for t in map(json.loads,(R/'runs/reference_dataset_v2/tables.jsonl').read_text().splitlines())};refs={}
 for r in map(json.loads,(R/'results/layout_offgrid_20261115/predictions_fem.jsonl').read_text().splitlines()):
  if r['method']=='full':refs[r['query_id']]=r
 qs=[q for q in read(R/'results/layout_offgrid_20261115/reference_plan.json')['queries'] if q['split']=='formal'];P=old.Predictors('to_asap7',read(R/'experiments/dac_characterization_20261114/selected_to_asap7.json'),learned=False)
 rows=[];checks=[];costs=[];slotrows=[]
 for tid in sorted({q['table_id'] for q in qs}):
  t=ts[tid];x=np.array(t['coordinates']);y=np.array(t['labels']);qq=sorted([q for q in qs if q['table_id']==tid],key=lambda q:q['geometry_hash']);q=np.array([a['coordinates'] for a in qq]);pred={}
  pred['mli'],tags=mli(x,y,q);assert set(tags)=={'complete_cell'}
  pred['openrcx_ideal'],_=openrcx(x,y,q,quantized=False)
  pred['openrcx_kernel'],meta=openrcx(x,y,q)
  native,inputtext=cpp(x,y,q,{})
  assert np.array_equal(native[:,:2],np.array([[r['width_index'],r['effective_separation']] for r in meta]))
  scale=np.maximum(np.sqrt(np.mean(y*y,0)),1e-30);err=float(np.max(abs(native[:,2:]-pred['openrcx_kernel'])/scale));assert err<1e-12
  # Native value pass through and learned injection share identical geometry-only slots.
  slots=[];ws=np.unique(x[:,0])
  for j,w in enumerate(ws):
   ids=np.flatnonzero(x[:,0]==w);ds=np.floor(x[ids,1]*1000+.5).astype(int);g=grid(ds,y[ids]);protected=set(ds//4)
   for slot,(eff,z) in sorted(g.items()):
    if slot*4>ds[0] and slot*4<ds[-1]-4 and slot not in protected:slots.append(dict(j=j,slot=slot,eff=eff,coordinate=[float(w),eff/1000,eff/1000],native=z))
  overrides={m:{} for m in ['pass','binary','full']}
  for a in slots:overrides['pass'][a['j'],a['slot']]=a['native']
  for method in ['binary','full']:
   begin=stamp()
   for off in range(0,len(slots),32):
    batch=slots[off:off+32];g,o,v,ix=query_table(x,y,np.array([a['coordinate'] for a in batch]),{k:v for k,v in old.public_input(t).items() if k!='coordinates'});z=P(method,g,o,v)[ix]
    for a,p in zip(batch,z):overrides[method][a['j'],a['slot']]=p
   costs.append(dict(table_id=tid,method=method,slots=len(slots),**elapsed(begin),Q_hash=digest([a['coordinate'] for a in slots])))
  for method,ov in overrides.items():
   pp,mm=openrcx(x,y,q,override=ov);cc,inp=cpp(x,y,q,ov);err2=float(np.max(abs(pp-cc[:,2:])/scale));assert err2<1e-12
   if method=='pass':assert np.allclose(pp,pred['openrcx_kernel'],rtol=1e-14,atol=1e-28)
   else:pred[method+'_compute']=cc[:,2:]
   (O/f'harness_{tid}_{method}.txt').write_text(inp)
   checks.append(dict(table_id=tid,mode=method,queries=len(q),slots=len(ov),max_scaled_cpp_python_error=err2,retrieved_injected=sum(a['path']=='injected' for a in mm)))
  for a in slots:slotrows.append(dict(table_id=tid,width_index=a['j'],slot=a['slot'],effective_sep_dbu=a['eff'],coordinates=a['coordinate'],native=a['native'].tolist(),binary=overrides['binary'][a['j'],a['slot']].tolist(),full=overrides['full'][a['j'],a['slot']].tolist()))
  for method,p in pred.items():
   for i,a in enumerate(qq):rows.append(dict(query_id=a['query_id'],table_id=tid,process=t['process_id'],family=t['family'],method=method,prediction=p[i].tolist(),reference=refs[a['query_id']]['reference'],components=t['target_names'],unit='F/m',occurrence_count=a['occurrence_count'],sampling_probability=a['sampling_probability'],native_meta=meta[i],S_hash=digest([x.tolist(),y.tolist()])))
  print('physical',tid,len(q),'slots',len(slots),flush=True)
 with gzip.open(O/'physical_predictions.jsonl.gz','wt') as f:
  for r in rows:f.write(json.dumps(r)+'\n')
 with gzip.open(O/'physical_slots.jsonl.gz','wt') as f:
  for r in slotrows:f.write(json.dumps(r)+'\n')
 csvwrite(O/'physical_preparation.csv',costs);write(O/'physical_checks.json',dict(passed=True,checks=checks,**elapsed(start),scope='same 71 symmetric 2D templates; same 153 S per context; scalar projection wrapper uses third scalar channel for diagonal only, not native resistance; no new field solve'))
if __name__=='__main__':main()
