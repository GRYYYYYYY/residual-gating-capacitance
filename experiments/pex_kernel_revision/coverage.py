"""All four holdouts; shared deterministic S/Q; reuse Full accumulators."""
from common import *
import importlib.util,gzip,collections,argparse
import numpy as np,torch
from kernels import mli,openrcx,independent_axes
# Load prior predictors without importing this directory's common as theirs.
sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
saved=sys.modules.pop('common',None)
spec=importlib.util.spec_from_file_location('prior_predict',R/'experiments/dac_characterization_20261114/evaluate.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
from unified.episodes import encode
from pdkcap.sampling import mask
from pdkcap.metrics import record
from pdkcap.round3_support import SEGMENTS

def run(domain,pilot=False):
 pin();start=stamp();ts=old.tables(domain,'confirmation');P=old.Predictors(domain,read(R/f'experiments/dac_characterization_20261114/selected_{domain}.json'),learned=False)
 cfg=read(R/'configs/paper_models.json')[domain];original={}
 with gzip.open(R/'runs'/cfg['record_run']/'records.jsonl.gz','rt') as f:
  for l in f:
   r=json.loads(l)
   if r['method']==cfg['method'] and str(r['training_seed'])=='ensemble' and r['ratio'] is not None and r['segment']!='all':original.setdefault((r['table_id'],r['protocol'],r['ratio'],r['mask_seed']),[]).append(r)
 inventory=[];seen={};failures=[];rows=0
 dest=O/f'coverage_{domain}{"_pilot" if pilot else ""}.jsonl.gz'
 with gzip.open(dest,'wt') as f:
  for ti,t in enumerate(ts[:1] if pilot else ts):
   x=np.asarray(t['coordinates']);y=np.asarray(t['labels']);g=old.public_input(t)
   for protocol in ['mcar','block','extrapolation']:
    for ratio in [.1,.3,.5,.7]:
     for seed in [11,29,47,71,101]:
      o,q=mask(x,protocol,ratio,seed);key=(t['table_id'],protocol,ratio,seed);source=original[key];assert sorted(i for rr in source for i in rr['scored_indices'])==q.tolist()
      sh=digest([t['table_id'],o.tolist(),q.tolist()]);duplicate=seen.get(sh);seen.setdefault(sh,[protocol,ratio,seed])
      pred={};p,st=mli(x[o],y[o],x[q]);pred['mli_sparse']=p
      complete=np.array([s=='complete_cell' for s in st]);scale=2000. if t['process_id']=='gf180' else 1000.
      # Rank-2 diagonal geometry is scalar-projected kernel analysis, not native diagonal API.
      try:pred['openrcx_kernel']=openrcx(x[o],y[o],x[q],scale)[0];valid=True
      except (ValueError,KeyError) as e:valid=False;failures.append(dict(key=list(key),reason=str(e)));pred['openrcx_kernel']=None
      pred['binary']=P('binary',g,o,y[o])[q]
      pred['anchor']=P('anchor',g,o,y[o])[q];pred['numerical_only']=P('gp',g,o,y[o])[q]
      inv=dict(domain=domain,table_id=t['table_id'],protocol=protocol,requested_holdout=ratio,seed=seed,n_total=len(x),support_count=len(o),query_count=len(q),actual_holdout=len(q)/len(x),rank=len(independent_axes(x[o])),complete_cell_queries=int(complete.sum()),sparse_extension_queries=st.count('sparse_support_extension'),clamped_queries=st.count('explicit_clamp'),inside_count=sum(rr['n'] for rr in source if rr['segment']!='outside'),outside_count=sum(rr['n'] for rr in source if rr['segment']=='outside'),SQ_hash=sh,duplicate_of=json.dumps(duplicate),openrcx_applicable=valid)
      inventory.append(inv)
      for rr in source:
       r=dict(rr,method='full',domain_setting=domain,SQ_hash=sh,origin='reused original accumulator');f.write(json.dumps(r)+'\n');rows+=1
       idx=rr['scored_indices'];ix=np.searchsorted(q,idx)
       for method,prediction in pred.items():
        if prediction is None:continue
        r=record(t,y[idx],prediction[ix],method=method,training_seed='ensemble',protocol=protocol,ratio=ratio,mask_seed=seed,segment=rr['segment'],scored_indices=idx,domain_setting=domain,SQ_hash=sh,origin='new matched evaluation')
        f.write(json.dumps(r)+'\n');rows+=1
      # Complete-cell comparison is a geometry-defined subset. Full individual outputs
      # are not in archived accumulators, so do not fabricate its subset scores.
      if complete.any():
       ii=np.flatnonzero(complete)
       for method,prediction in pred.items():
        if prediction is not None:
         r=record(t,y[q[ii]],prediction[ii],method=method,training_seed='ensemble',protocol=protocol,ratio=ratio,mask_seed=seed,segment='complete_cell',scored_indices=q[ii].tolist(),domain_setting=domain,SQ_hash=sh,origin='geometry-selected complete-cell subset')
         f.write(json.dumps(r)+'\n');rows+=1
   print(domain,ti+1,'/',len(ts),'cpu',round(elapsed(start)['cpu_s'],1),flush=True)
   f.flush()
 csvwrite(O/f'coverage_inventory_{domain}{"_pilot" if pilot else ""}.csv',inventory)
 write(O/f'coverage_{domain}{"_pilot" if pilot else ""}_receipt.json',dict(**elapsed(start),tables=min(1,len(ts)) if pilot else len(ts),episodes=len(inventory),rows=rows,failures=failures,full_reused_sha256=sha(R/'runs'/cfg['record_run']/'records.jsonl.gz'),models='unchanged Full/Binary three members',numerical_only_selection=read(R/f'experiments/dac_characterization_20261114/selected_{domain}.json')))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('domain');ap.add_argument('--pilot',action='store_true');a=ap.parse_args();run(a.domain,a.pilot)
