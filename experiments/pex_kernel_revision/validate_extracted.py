"""Verify extracted pinned source against actual native returns, not FEM truth."""
from common import *
import numpy as np,subprocess
from kernels import openrcx

def main():
 old=R/'results/layout_offgrid_20261115';ts=read(old/'native_supports.json');qs=read(old/'native_replay_plan.json');rows=[]
 for tid in sorted({q['rule_key'] for q in qs}):
  t=ts[tid];qq=[q for q in qs if q['rule_key']==tid];x=np.array(t['coordinates']);y=np.column_stack([np.array(t['labels']),np.zeros(len(x))]);scale=qq[0]['coordinate_scale'];ws=np.unique(x[:,0]);lines=['1',f'{len(ws)} {len(qq)} 0']
  for w in ws:
   ids=np.flatnonzero(x[:,0]==w);ids=ids[np.argsort(x[ids,1])];lines.append(f'{round(w*scale)} {len(ids)}')
   for i in ids:lines.append(' '.join(map(str,[int(np.floor(x[i,1]*scale+.5)),*y[i]])))
  for q in qq:lines.append(' '.join(map(str,q['raw_dbu'])))
  p=subprocess.run([str(O/'pinned_kernel')],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True);out=np.array([[float(a) for a in l.split()] for l in p.stdout.splitlines()]);sc=max(float(np.max(abs(y))),1e-30)
  for q,z in zip(qq,out):
   expected=np.array(q['reference']);err=float(np.max(abs(z[2:4]-expected))/sc);assert err<1e-12 and z[1]==q['effective_dbu'][1],(q['query_id'],err,z,q['effective_dbu'])
   rows.append(dict(query_id=q['query_id'],max_support_scaled_error=err,returned_sep=int(z[1]),expected_sep=q['effective_dbu'][1]))
 write(O/'extracted_native_validation.json',dict(passed=True,queries=len(rows),max_scaled_error=max(r['max_support_scaled_error'] for r in rows),rows=rows,reference='actual OpenRCX returns; finite non-sentinel; not physics'))
 print('extracted source/native returns matched',len(rows))
if __name__=='__main__':main()
