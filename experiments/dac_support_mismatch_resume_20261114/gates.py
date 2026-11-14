"""Stage identities and immutable-input gates; absent receipt always rejects."""
import json
from paths import *
def receipt(root,name):
 r=json.loads((root/name).read_text())
 if r.get('status')!='success' or r.get('attempt_id')!=ATTEMPT:raise ValueError('invalid success identity')
 for p,h in r.get('artifacts',{}).items():
  if sha(ROOT/p)!=h:raise ValueError('success artifact hash mismatch: '+p)
 return r

def prepare_gate(root=OUT):return receipt(root,'PREPARE_SUCCESS.json')
def freeze_gate(root=OUT):
 prepare_gate(root);r=receipt(root,'FREEZE_SUCCESS.json')
 if r['prepare_sha256']!=sha(root/'PREPARE_SUCCESS.json'):raise ValueError('prepare binding mismatch')
 if r['freeze_sha256']!=sha(root/'FREEZE_MANIFEST.json'):raise ValueError('freeze binding mismatch')
 f=json.loads((root/'FREEZE_MANIFEST.json').read_text())
 for p,h in f.items():
  if sha(ROOT/p)!=h:raise ValueError('frozen dependency changed: '+p)
 return json.loads((root/'FROZEN_PLAN.yaml').read_text())
def worker_gate(pilot,root=OUT):
 plan=freeze_gate(root)
 if not pilot:
  r=receipt(root,'FEASIBILITY_PASS.json')
  if r['freeze_sha256']!=sha(root/'FREEZE_MANIFEST.json'):raise ValueError('feasibility freeze mismatch')
 return plan

def endpoint_gate(root=OUT):
 plan=worker_gate(False,root)
 for unit in plan['unit_order']:
  p=root/'checkpoints'/unit;r=json.loads((p/'COMPLETED.json').read_text())
  if r['updates']!=2000 or r['unit']!=unit or r['freeze_sha256']!=sha(root/'FREEZE_MANIFEST.json') or sha(p/'checkpoint.pt')!=r['checkpoint_sha256']:raise ValueError('invalid endpoint '+unit)
 return plan
