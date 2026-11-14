"""One frozen endpoint; pilot is its first 20 updates and is resumed exactly."""
from core import *
import argparse,time
ap=argparse.ArgumentParser();ap.add_argument('arch',choices=['Full','binary']);ap.add_argument('arm',choices=['H','L']);ap.add_argument('seed',type=int);ap.add_argument('--pilot',action='store_true');args=ap.parse_args()
plan=worker_gate(args.pilot);a,arm,seed=args.arch,args.arm,args.seed;unit=f'{a}_{arm}_s{seed}'
torch.manual_seed(seed);model,state,cfg=load(a,seed)
assert sha(source(a,seed))==next(x['sha256'] for x in json.loads((OUT/'CHECKPOINT_LINEAGE.json').read_text()) if x['architecture']==a and x['seed']==seed)
optimizer=torch.optim.AdamW(model.parameters(),lr=plan['learning_rate'],weight_decay=plan['weight_decay'])
resume=OUT/'resume'/f'{unit}.pt';dest=OUT/'checkpoints'/unit
resume.parent.mkdir(exist_ok=True);dest.mkdir(parents=True,exist_ok=True)
assert not (dest/'checkpoint.pt').exists()
startstep=0
if resume.exists():
 pr=json.loads((dest/'PILOT.json').read_text());assert sha(resume)==pr['resume_sha256'] and pr['freeze_sha256']==sha(OUT/'FREEZE_MANIFEST.json')
 r=torch.load(resume,map_location='cpu',weights_only=True);assert r['freeze_sha256']==sha(OUT/'FREEZE_MANIFEST.json');model.load_state_dict(r['state_dict'],strict=True);optimizer.load_state_dict(r['optimizer']);torch.set_rng_state(r['rng']);startstep=r['step']
assert not args.pilot or (startstep==0 and seed==0)
assert args.pilot or startstep==(20 if seed==0 else 0)
stop=20 if args.pilot else plan['updates'];ep=episodes()[seed];train={t['table_id']:t for t in verified_tables('train')}
start=time.perf_counter();startcpu=time.process_time();history=[]
for step in range(startstep,stop):
 model.train();optimizer.zero_grad();losses=[]
 for e in ep[step]:
  t=train[e['table_id']];o=e[arm];q=e['Q'];y=np.asarray(t['labels'],float);encoded=encode(public_input(t),o,y[o],state['scales'],names=names(a))
  losses.append(episode_loss(model,encoded,q,y,cfg['huber_delta'],cfg['span_weight']))
 loss=sum(losses)/4
 if not torch.isfinite(loss):raise RuntimeError(f'NONFINITE_LOSS at {unit} step{step+1}')
 loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.)
 if not torch.isfinite(norm):raise RuntimeError(f'NONFINITE_GRAD at {unit} step{step+1}')
 optimizer.step()
 if step%100==0 or step==stop-1:
  row=dict(step=step+1,loss=float(loss.detach()),cpu_seconds=time.process_time()-startcpu,wall_seconds=time.perf_counter()-start);history.append(row);print(json.dumps(row),flush=True)
if args.pilot:
 torch.save(dict(state_dict=model.state_dict(),optimizer=optimizer.state_dict(),rng=torch.get_rng_state(),step=stop,freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json')),resume)
 write(dest/'PILOT.json',dict(unit=unit,attempt_id=ATTEMPT,status='success',freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json'),updates=stop,startstep=startstep,training_cpu_s=time.process_time()-startcpu,training_wall_s=time.perf_counter()-start,history=history,resume_sha256=sha(resume)))
else:
 state['state_dict']=model.state_dict();torch.save(state,dest/'checkpoint.pt')
 write(dest/'COMPLETED.json',dict(unit=unit,architecture=a,arm=arm,seed=seed,updates=stop,startstep=startstep,source_sha256=sha(source(a,seed)),checkpoint_sha256=sha(dest/'checkpoint.pt'),freeze_sha256=sha(OUT/'FREEZE_MANIFEST.json'),training_cpu_s=time.process_time()-startcpu,training_wall_s=time.perf_counter()-start,history=history,optimizer='AdamW reset at step0; pilot exact resume',state_keys=sorted(state['state_dict'])))
print('ENDPOINT_DONE' if not args.pilot else 'PILOT_DONE',unit,flush=True)
