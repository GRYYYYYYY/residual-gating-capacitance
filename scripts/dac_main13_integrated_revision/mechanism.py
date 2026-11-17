"""Frozen member candidates, source-only fixed fusion, and matched-control scoring."""
from pathlib import Path
import os,sys,json,csv,gzip,time,argparse,collections
import numpy as np
import torch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R));sys.path.insert(0,str(R/'experiments/dac_characterization_20261114'))
import evaluate as old
from unified.episodes import encode,stack
from unified.basis import BASIS
from unified.train import build_model
from unified.score import dependency_group,load_members
from pdkcap.sampling import mask
from pdkcap.metrics import record
from pdkcap.round3_support import SEGMENTS
from train_controls import NumericalGate
sys.path.insert(0,str(R/'experiments/pex_kernel_revision'))
from kernels import mli
O=R/'results/dac_main13_integrated_revision/main13_20261117/mechanism';O.mkdir(parents=True,exist_ok=True)
torch.set_num_threads(1)
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def call(model,b,gate=False):return model(b['features'],b['anchor'],b['gate'],b['delta'],b['valid'],padding=b['padding'],clamp_lower=b['lower'],clamp_upper=b['upper'],inside=b['inside'],return_gate=gate)
def candidates(model,b):
 p,g=call(model,b,True)
 d=torch.cat([b['delta'],g['residual'].unsqueeze(2),g['clamped'].unsqueeze(2)],2)
 return p,g,torch.nan_to_num(d),g['valid']
def fit(domain,P):
 path=O/f'{domain}_fixed_weights.json'
 if path.exists():return np.array(json.loads(path.read_text())['weights'])
 start=time.perf_counter();deltas=[[] for _ in range(3)];valids=[];anchors=[];ys=[];rw=[];ids=[]
 ts=old.tables(domain,'train');counts=collections.Counter(t['family'] for t in ts)
 with torch.inference_mode():
  for t in ts:
   for proto in ['mcar','block','extrapolation']:
    idx,q=mask(t['coordinates'],proto,.3,11);truth=np.asarray(t['labels']);e=encode(old.public_input(t),idx,truth[idx],P.scales);b=stack([e]);scale=np.asarray(e['scales'])
    for i,m in enumerate(P.members):
     _,_,d,v=candidates(m,b);deltas[i].append(d[0,q].numpy().copy())
    valids.append(v[0,q].numpy().copy());anchors.append(b['anchor'][0,q].numpy().copy());ys.append(truth[q]/scale);rw.extend([1/(counts[t['family']]*len(q))]*len(q));ids.append([t['table_id'],proto,idx.tolist(),q.tolist()])
 a=torch.tensor(np.concatenate(anchors));y=torch.tensor(np.concatenate(ys),dtype=torch.float32);v=torch.tensor(np.concatenate(valids),dtype=torch.float32).unsqueeze(-1);wrow=torch.tensor(rw);wrow=wrow/wrow.sum();weights=[]
 for ds in deltas:
  d=torch.tensor(np.concatenate(ds));logits=torch.zeros((d.shape[1],d.shape[2]),requires_grad=True);opt=torch.optim.Adam([logits],lr=.05)
  for step in range(300):
   opt.zero_grad();w=logits.softmax(0).unsqueeze(0)*v;w=w/w.sum(1,keepdim=True);p=(a+(w*d).sum(1)).clamp(min=0);loss=(torch.nn.functional.huber_loss(p,y,reduction='none').mean(1)*wrow).sum();loss.backward();opt.step()
  weights.append(logits.detach().softmax(0).numpy().tolist())
 save(path,dict(weights=weights,fit_ids=ids,steps=300,lr=.05,loss='family/table balanced source-scaled Huber',configuration_selection='one frozen configuration; final step, no target selection',candidate_order=BASIS,wall_s=time.perf_counter()-start))
 return np.array(weights)
def fixed(d,v,w,a):
 z=w[None]*v[:,:,None];z=z/z.sum(1,keepdims=True)
 return np.maximum(a+(z*d).sum(1),0)
def load_controls(domain):
 result={}
 for variant in ['numerical_gate','no_agreement']:
  ms=[]
  for seed in range(3):
   p=O.parent/'controls'/f'{domain}_{variant}_s{seed}';assert (p/'COMPLETED.json').exists(),p
   state=torch.load(p/'checkpoint.pt',map_location='cpu',weights_only=True);cfg=json.loads((p/'FROZEN.json').read_text())['config'];base=build_model(cfg,state['features_in'],state['gate_in'],state['experts'],state['targets']);m=NumericalGate(base) if variant=='numerical_gate' else base;m.load_state_dict(state['state_dict']);m.eval();ms.append(m)
  result[variant]=ms
 return result
def run(domain,controls=False):
 start=time.perf_counter();source_hash=old.sha(Path(__file__));P=old.Predictors(domain,learned=False);fw=fit(domain,P);ms=load_controls(domain) if controls else {}
 suffix='controls' if controls else 'frozen';dest=O/f'{domain}_{suffix}.jsonl.gz';raw=O/f'{domain}_candidate_outputs.jsonl.gz';scores=O/f'{domain}_candidate_scores.jsonl.gz'
 assert not dest.exists(),dest
 inv={r['SQ_hash'] for r in csv.DictReader((R/f'results/pex_kernel_revision/coverage_inventory_{domain}.csv').open()) if r['openrcx_applicable']=='True'}
 import hashlib
 n=0;sample_checks=[]
 with gzip.open(dest,'wt') as f,gzip.open(raw if not controls else O/f'{domain}_controls_detail.jsonl.gz','wt') as rawf,gzip.open(O/f'{domain}_{suffix}_mli_strata.jsonl.gz','wt') as mf,torch.inference_mode():
  for ti,t in enumerate(old.tables(domain,'confirmation')):
   truth=np.asarray(t['labels']);public=old.public_input(t)
   for proto in ['mcar','block','extrapolation']:
    for ratio in [.1,.3,.5,.7]:
     for seed in [11,29,47,71,101]:
      idx,q=mask(t['coordinates'],proto,ratio,seed);h=hashlib.sha256(json.dumps([t['table_id'],idx.tolist(),q.tolist()],sort_keys=True).encode()).hexdigest()
      if h not in inv:continue
      e=encode(public,idx,truth[idx],P.scales);b=stack([e]);scale=np.asarray(e['scales']);preds=collections.defaultdict(list)
      sx=np.asarray(t['coordinates'])[idx];span=np.ptp(sx,axis=0);span[span==0]=1
      meta=dict(domain=domain,table_id=t['table_id'],process_id=t['process_id'],family=t['family'],dependency_group=dependency_group(t),protocol=proto,ratio=ratio,mask_seed=seed,SQ_hash=h,support_affine_rank=int(np.linalg.matrix_rank((sx-sx[0])/span)),n_support=len(idx),n_total_coordinates=len(t['coordinates']))
      if controls:
       for name,members in ms.items():
        for m in members:preds[name].append(call(m,b)[0,:e['n']].numpy()*scale)
      else:
       for i,m in enumerate(P.members):
        p,g,d,v=candidates(m,b);dn=d[0,:e['n']].numpy();vn=v[0,:e['n']].numpy();a=b['anchor'][0,:e['n']].numpy();weights=g['weights'][0,:e['n']].numpy()
        preds['full_replay'].append(p[0,:e['n']].numpy()*scale);preds['fixed_fusion'].append(fixed(dn,vn,fw[i],a)*scale)
        rawf.write(json.dumps(dict(**meta,member=i,query_indices=q.tolist(),support_indices=idx.tolist(),anchor=(a[q]*scale).tolist(),candidate=((a[q,None,:]+dn[q])*scale).tolist(),valid=vn[q].tolist(),weights=weights[q].tolist(),weighted_correction=(weights[q]*dn[q]*scale).tolist(),support_features=e['gate'][q].tolist(),inside=e['inside'][q].tolist(),segment=e['segment'][q].tolist(),scale=scale.tolist()),allow_nan=False)+'\n')
        # Candidate diagnostics are scored later by score_candidates.py;
        # their errors are never available to the predictor or gate.
       for variant in ['residual','binary']:
        for i,m in enumerate(P.control[variant]):
         hidden=m.encoder(m.input(b['features']),src_key_padding_mask=b['padding']);res=m.residual(hidden);alpha=torch.ones_like(res)
         if variant=='binary':
          logits=m.gate(torch.cat([hidden,b['gate']],-1)).reshape(*hidden.shape[:2],2,m.targets)+m.gate_bias.view(1,1,2,1);alpha=torch.softmax(logits/(torch.nn.functional.softplus(m.log_temperature)+1e-3),2)[:,:,1]
         out=(b['anchor']+alpha*res).clamp(min=0);preds[variant+'_replay'].append(out[0,:e['n']].numpy()*scale)
         rawf.write(json.dumps(dict(**meta,method=variant,member=i,query_indices=q.tolist(),raw_residual=(res[0,q].numpy()*scale).tolist(),alpha=alpha[0,q].numpy().tolist(),prediction=(out[0,q].numpy()*scale).tolist()),allow_nan=False)+'\n')
      if not controls:
       mp,status=mli(np.asarray(t['coordinates'])[idx],truth[idx],np.asarray(t['coordinates'])[q])
       for name,pp in [('mli_sparse',mp)]+[(name,np.mean(parts,0)[q]) for name,parts in preds.items()]:
        for tag in sorted(set(status)):
         for region in ['inside','outside']:
          take=np.array([j for j,st in enumerate(status) if st==tag and ('outside' if e['segment'][q[j]]==0 else 'inside')==region],int)
          if len(take):mf.write(json.dumps(record(t,truth[q[take]],pp[take],method=name,training_seed='ensemble',protocol=proto,ratio=ratio,mask_seed=seed,segment=region,mli_status=tag,scored_indices=q[take].tolist(),dependency_group=dependency_group(t)),allow_nan=False)+'\n')
      for name,parts in preds.items():
       p=np.mean(parts,0);p[idx]=truth[idx]
       for k,seg in enumerate(SEGMENTS):
        ii=q[e['segment'][q]==k]
        if len(ii):f.write(json.dumps(record(t,truth[ii],p[ii],method=name,training_seed='ensemble',protocol=proto,ratio=ratio,mask_seed=seed,segment=seg,scored_indices=ii.tolist(),SQ_hash=h,dependency_group=dependency_group(t)),allow_nan=False)+'\n')
      n+=1
   if (ti+1)%25==0 or ti+1==len(old.tables(domain,'confirmation')):print(domain,suffix,ti+1,'tables',n,'episodes',round(time.perf_counter()-start,1),'s',flush=True)
 assert old.sha(Path(__file__))==source_hash,'running source drift'
 save(O/f'{domain}_{suffix}_completed.json',dict(episodes=n,wall_s=time.perf_counter()-start,runner_sha256=source_hash,candidate_order=BASIS,support_feature_schema='pdkcap.round2_model.support_geometry: density/log-distance/log-span/inside/log-envelope; pdkcap.round3_support.describe: segment one-hot/independent-axis count/log-typical-neighbor/width-valid/coordinate coverage/log-variation/signed-log-slopes/signed-log-curvature; unified.basis.context_vector appended',support_feature_source_sha256=old.sha(R/'pdkcap/round3_support.py'),diagnostic_label_boundary='candidate generation accepts public input and S labels only; independent score_candidates.py reads reference after frozen output completion',controls=controls))
def selection(domain):
 P=old.Predictors(domain,learned=False);w=fit(domain,P);rows=[]
 with torch.inference_mode():
  for t in old.tables(domain,'val'):
   y=np.asarray(t['labels'])
   for proto in ['mcar','block','extrapolation']:
    o,q=mask(t['coordinates'],proto,.3,11);e=encode(old.public_input(t),o,y[o],P.scales);b=stack([e]);pred=[]
    for i,m in enumerate(P.members):
     _,_,d,v=candidates(m,b);pred.append(fixed(d[0,:e['n']].numpy(),v[0,:e['n']].numpy(),w[i],b['anchor'][0,:e['n']].numpy())*e['scales'])
    rows.append(record(t,y[q],np.mean(pred,0)[q],method='fixed_fusion',protocol=proto))
 with gzip.open(O/f'{domain}_source_selection.jsonl.gz','wt') as f:
  for r in rows:f.write(json.dumps(r)+'\n')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--domain',required=True);a.add_argument('--controls',action='store_true');a.add_argument('--selection',action='store_true');v=a.parse_args()
 if v.selection:selection(v.domain)
 else:run(v.domain,v.controls)
