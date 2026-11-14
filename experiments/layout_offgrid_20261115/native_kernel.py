"""Native-validated reimplementation of rank-one compute-table lookup.
For finite non-sentinel ranges only. Never represents independent physics.
"""
import numpy as np

def predict_native(knots,values,query):
 x=np.asarray(knots,int);v=np.asarray(values,float);q=np.asarray(query,int)
 if np.any(np.diff(x)<=0):raise ValueError('strictly increasing knots required')
 out=[];effective=[]
 # extDistRCTable::mapInterpolate advances by 4 FROM each left knot,
 # writing floor(distance/4), not necessarily using global multiples of 4.
 grid={}
 for i in range(len(x)-1):
  for d in range(int(x[i]),int(x[i+1])+1,4):
   alpha=(d-x[i])/(x[i+1]-x[i]);grid[d//4]=(d,v[i]+alpha*(v[i+1]-v[i]))
 for d in q:
  if d<=x[0]:se,z=x[0],v[0]
  elif d>=x[-1]-4 and x[-1]>0:se,z=x[-1],v[-1]
  elif d//4 in grid:se,z=grid[d//4]
  else:raise ValueError('uninitialized compute-grid cell')
  out.append(z);effective.append(se)
 return np.array(out),np.array(effective)

if __name__=='__main__':
 import json
 from pathlib import Path
 R=Path(__file__).resolve().parents[2];O=R/'results/layout_offgrid_20261115'
 recs=[json.loads(l) for l in (O/'query_manifest.jsonl').read_text().splitlines()];out=[]
 # Original traces supply sentinel presence. This validation excludes those
 # special-tail tables, rather than silently substituting generic clamping.
 for case in sorted(set(r['process']+'/'+r['design'] for r in recs)):
  kk={}
  for line in (O/'native'/case/'trace.tsv').open():
   a=line.split('\t')
   if a[0]=='K':kk.setdefault(a[1],[]).append([int(a[3]),float(a[4]),float(a[5])])
  for r in recs:
   if r['process']+'/'+r['design']!=case or r['call_type']!='Q':continue
   k=np.array(kk.get(r['provenance']['table_pointer'],[]))
   if len(k)<2 or k[-1,0]==100000 or np.any(np.diff(k[:,0])<=0):continue
   try:p,se=predict_native(k[:,0],k[:,1:],[r['raw_dbu'][1]])
   except ValueError:continue
   err=float(np.max(abs(p[0]-r['native_prediction'])));scale=max(float(np.max(abs(k[:,1:]))),1e-30)
   out.append(dict(query_id=r['query_id'],occurrences=r['occurrence_count'],max_absolute=err,scale=scale,passed=bool(err<=1e-12*scale and se[0]==r['effective_dbu'][1])))
 summary=dict(identity='native-validated reimplementation, finite no-100000-sentinel tables only',queries=len(out),occurrences=sum(x['occurrences'] for x in out),passed=all(x['passed'] for x in out),max_scaled_error=max((x['max_absolute']/x['scale'] for x in out),default=None))
 (O/'native_validation.json').write_text(json.dumps(dict(summary=summary,rows=out),indent=2));print(summary)
