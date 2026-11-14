import sys
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from unified.queries import query_table
from pdkcap.round2_model import support_geometry
s=np.array([[0.,0.,0.],[1.,1.,0.],[2.,2.,0.]])+1
v=np.array([[1.],[2.],[4.]])
q=np.array([[1.5,1.5,1.],[1.5,2.,1.],[4.,4.,1.]])
g=support_geometry(s,v,q,np.ones(1))
assert g['inside'].tolist()==[True,False,False] # bbox alone incorrectly accepts q[1]
t,o,y,ix=query_table(s,v,q,dict(table_id='smoke',family='OVER'))
assert 'labels' not in t and np.array_equal(y,v) and np.array_equal(np.array(t['coordinates'])[ix],q)
try:query_table(s,v,q,dict(labels=[[1e30]]))
except ValueError:pass
else:raise AssertionError('query labels accepted')
try:query_table(np.vstack([s,s[0]]),np.vstack([v,999]),q,{})
except ValueError:pass
else:raise AssertionError('conflicting labels accepted')
print('PASS: affine-span classification, query-only boundary, conflicts, S-only values')
