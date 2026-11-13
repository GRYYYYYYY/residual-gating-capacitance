from common import *
from learning import Learned
from evaluate import trajectory
import torch,copy
rows=[];torch.set_num_threads(1)
for s in MODELS:
 learned=Learned(s);t=tables(s,'val')[0];c,q,snaps=trajectory(t,11,'farthest');o,v,_,_=snaps[0];poison=copy.deepcopy(t);yy=np.asarray(t['labels']);yy[np.setdiff1d(np.arange(len(yy)),o)]=1e30;poison['labels']=yy.tolist()
 for name in ('mlp_zero','mlp_adapt','cnp'):
  p=learned.predict(name,public_input(t),o,v);p2=learned.predict(name,public_input(poison),o,v);assert np.array_equal(p,p2)
  if name=='mlp_zero':assert np.array_equal(p,learned.predict(name,public_input(t),o,v*123))
 rows.append(dict(setting=s,new_baselines_label_blind=True,zero_mlp_support_independent=True))
write(ROOT/'results/dac_characterization_20261114/learned_boundary_checks.json',rows);print(rows)
