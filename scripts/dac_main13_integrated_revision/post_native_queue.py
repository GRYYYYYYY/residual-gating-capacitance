"""Single post-native worker; bounded deterministic queue, no duplicate submissions."""
from pathlib import Path
import sys,time,subprocess,json,os
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';S=Path(__file__).resolve().parent;start=time.time();logs=O/'post_native';logs.mkdir(exist_ok=True)
def wait_for(paths):
 while not all(p.exists() for p in paths):
  if time.time()-start>21600:raise TimeoutError('bounded post-native dependency wait')
  time.sleep(30)
def run(name,args,receipt):
 if receipt.exists():print('REUSE',name,flush=True);return
 with (logs/(name+'.log')).open('x') as f:
  p=subprocess.run([sys.executable,*map(str,args)],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=10800)
 if p.returncode:raise RuntimeError((name,p.returncode))
 print('DONE',name,flush=True)
if __name__=='__main__':
 (logs/'owner.json').write_text(json.dumps(dict(pid=os.getpid(),created=time.time(),dependency='native/matrix_completed.json',max_workers=1)))
 try:
  wait_for([O/'native/matrix_completed.json'])
  run('batching',[S/'batching.py'],O/'query_batching_tests.json')
  run('trace_accounting',[S/'trace_accounting.py'],O/'coverage_trace_alignment.json')
  for domain in ['public','reference','to_asap7']:
   run(domain+'_C2_source_selection',[S/'mechanism.py','--domain',domain,'--selection'],O/f'mechanism/{domain}_source_selection.jsonl.gz')
   run(domain+'_frozen_diagnostics',[S/'mechanism.py','--domain',domain],O/f'mechanism/{domain}_frozen_completed.json')
  for domain in ['public','reference','to_asap7']:
   wait_for([O/'controls'/f'{domain}_{v}_s{s}/COMPLETED.json' for v in ['numerical_gate','no_agreement'] for s in range(3)])
   run(domain+'_matched_controls',[S/'mechanism.py','--domain',domain,'--controls'],O/f'mechanism/{domain}_controls_completed.json')
  (logs/'completed.json').write_text(json.dumps(dict(status='PASS',wall_s=time.time()-start)))
 except Exception as e:
  (logs/'failed.json').write_text(json.dumps(dict(error=repr(e),wall_s=time.time()-start)));raise
