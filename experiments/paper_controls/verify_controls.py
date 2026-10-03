import sys,copy,json
from pathlib import Path
from run_controls import ROOT,HERE,config_for,SimpleControl
from score_controls import affine_predict
import numpy as np
import torch
from unified import train
from unified.episodes import encode,stack
from pdkcap.common import read_tables
from pdkcap.sampling import mask

def main():
 torch.set_num_threads(1)
 for domain in ['public','reference','to_asap7']:
  cfg,_=config_for(domain,0);table=next(t for t in read_tables(cfg['data']) if t['partition']=='train')
  scales=train.load_scales(cfg['scales_from']);truth=np.asarray(table['labels']);o,q=mask(table['coordinates'],'block',.3,11)
  full=encode(table,o,truth[o],scales);simple=encode(table,o,truth[o],scales,names=('linear',))
  for k in ['features','anchor','gate','lower','upper','inside','segment']:np.testing.assert_array_equal(full[k],simple[k])
  altered=copy.deepcopy(table);alt=np.asarray(altered['labels']);alt[q]=1e5;altered['labels']=alt.tolist()
  blind=encode(altered,o,truth[o],scales,names=('linear',))
  for k in ['features','anchor','gate','lower','upper','inside']:np.testing.assert_array_equal(simple[k],blind[k])
  b=stack([simple]);base=train.build_model(cfg,simple['features'].shape[1],simple['gate'].shape[1],11,simple['targets'])
  for variant in ['residual','binary']:
   model=SimpleControl(copy.deepcopy(base),variant);model.eval()
   with torch.no_grad():
    out=model(b['features'],b['anchor'],b['gate'],b['delta'],b['valid'],padding=b['padding'])
    raw=model.residual(model.encoder(model.input(b['features']),src_key_padding_mask=b['padding']))
    expected=torch.clamp(b['anchor']+raw*(.5 if variant=='binary' else 1.),min=0)
    torch.testing.assert_close(out,expected)
 x=np.array([[0.],[1.],[2.]])
 np.testing.assert_allclose(affine_predict(x,2*x+3,np.array([[3.],[4.]]),2),[[9],[11]],rtol=1e-6)
 x=np.array([[0.,0.],[0.,1.],[1.,0.],[1.,1.]])
 q=np.array([[2.,2.],[3.,1.]])
 np.testing.assert_allclose(affine_predict(x,(2*x[:,0]+3*x[:,1]+4)[:,None],q,4),(2*q[:,0]+3*q[:,1]+4)[:,None],rtol=1e-6)
 print('PASS: same tokens/support features, hidden-label independence, residual/binary identities, affine recovery outside support in 1D and 2D.')
if __name__=='__main__':main()
