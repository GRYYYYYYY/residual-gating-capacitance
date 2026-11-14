import json,copy,tempfile,sys,subprocess
from unittest.mock import patch
import numpy as np
from paths import *
from checks import assert_same_encoded
from gates import prepare_gate,freeze_gate,worker_gate
from driver import run_chain
checks=[]
a={k:np.ones((2,2)) for k in ['features','anchor','gate','lower','upper']};a.update(valid=np.array([[True,False]]),delta=np.array([[[1.,2.],[np.nan,np.nan]]]),inside=np.array([True,False]),observed=np.array([0]),values=np.ones((1,2)),scales=np.ones(2))
assert_same_encoded(a,copy.deepcopy(a));checks.append('valid finite entries and matching raw unavailable NaNs pass')
def rejected(name,f):
 try:f()
 except (ValueError,FileNotFoundError):checks.append(name+' rejected');return
 raise AssertionError('regression failed to reject '+name)
for bad in [np.nan,np.inf]:
 x=copy.deepcopy(a);x['delta'][0,0,0]=bad;rejected('common applicable '+str(bad),lambda:assert_same_encoded(x,copy.deepcopy(x)))
x=copy.deepcopy(a);x['delta'][0,1]=0;rejected('zero unavailable sentinel',lambda:assert_same_encoded(a,x))
x=copy.deepcopy(a);x['delta'][0,0,0]+=1;rejected('finite delta change',lambda:assert_same_encoded(a,x))
x=copy.deepcopy(a);x['valid'][0,1]=True;rejected('valid-mask change',lambda:assert_same_encoded(a,x))
x=copy.deepcopy(a);x['delta']=x['delta'][:,:,:1];rejected('delta shape change',lambda:assert_same_encoded(a,x))
x=copy.deepcopy(a);x['features'][0,0]=np.nan;rejected('numeric feature NaN',lambda:assert_same_encoded(x,copy.deepcopy(x)))
idx={'H':[0,2,4],'L':sorted(int(i) for i in [np.int64(4),np.int64(0)]),'Q':[1,3]};assert json.loads(json.dumps(idx))==idx;checks.append('JSON exact roundtrip')
with tempfile.TemporaryDirectory() as td:
 root=Path(td)
 rejected('no prepare success',lambda:prepare_gate(root))
 rejected('no freeze success pilot',lambda:worker_gate(True,root))
 with patch('gates.freeze_gate',return_value={}):rejected('no matching feasibility formal',lambda:worker_gate(False,root))
 marker=root/'should_not_exist'
 try:run_chain([[sys.executable,'-c','raise SystemExit(7)'],[sys.executable,'-c',f'open({str(marker)!r},"w").write("bad")']])
 except subprocess.CalledProcessError as e:assert e.returncode==7
 assert not marker.exists();checks.append('failed prepare command prevents downstream command')
used,eng,rows=accounting();assert used>=150.849287 and SETTINGS['prior_debit_cpu_seconds']==150.849287;assert SETTINGS['new_administrative_debit_seconds']==30;checks.append('prior debit incl old60 carried once; new30 separate')
atomic_json(OUT/'REGRESSION_SUCCESS.json',dict(status='success',attempt_id=ATTEMPT,checks=checks,artifacts={str(CODE.relative_to(ROOT)/n):sha(CODE/n) for n in ['regression.py','checks.py','gates.py','driver.py','budget.py','paths.py','ATTEMPT.json']}))
print('REGRESSION_PASS',len(checks),flush=True)
