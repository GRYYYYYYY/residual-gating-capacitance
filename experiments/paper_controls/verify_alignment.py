import json,gzip
from pathlib import Path
from run_controls import HERE,ROOT,ARCHIVE,config_for
from unified.workspace import file_hash

def rows(path,method):
 out={}
 with gzip.open(path,'rt') as f:
  for line in f:
   r=json.loads(line)
   if r['method']!=method or r['ratio']!=.3 or r['protocol'] not in ['mcar','block','extrapolation']:continue
   key=(r['table_id'],r['protocol'],r['mask_seed'],r['segment'])
   assert key not in out
   out[key]={k:r.get(k) for k in ['n','squared_truth','scored_indices','dependency_group','training_scale']}
 return out

def verify_released_input(path, original_hash):
 path=Path(path).resolve()
 actual=file_hash(path)
 if actual==original_hash:return
 # Release exports anonymize metadata paths, preserving numerical payloads.
 manifest=json.loads((ROOT/'database/files.json').read_text())
 with gzip.open(ROOT/'database/files-extended.json.gz','rt') as f:manifest+=json.load(f)
 relative=str(path.relative_to(ARCHIVE.resolve()))
 entry=next(e for e in manifest if e['path']==relative)
 assert entry['source_sha256']==original_hash,(relative,'source hash')
 assert entry['sha256']==actual,(relative,'export hash')

def main():
 reports={}
 for domain,run,method in [('public','conf_public_holdout','sace_r_holdout'),('reference','conf_v10_reference','v10_all'),('to_asap7','conf_v10_to_asap7','v10_all')]:
  for seed in range(3):
   cfg,p=config_for(domain,seed);r=json.loads(p.read_text())
   verify_released_input(cfg['data'],r['data_sha256'])
   verify_released_input(cfg['scales_from'],r['scales_sha256'])
  f=HERE/'scores'/domain/'affine_selection.json';chosen=json.loads(f.read_text())['selected']
  old=rows(ARCHIVE/'runs'/run/'records.jsonl.gz',method)
  new=rows(HERE/'scores'/domain/'affine_confirmation.jsonl.gz',chosen)
  assert old==new,domain
  report=dict(affine_matches_headline=True,matched_record_count=len(new))
  learned=HERE/'scores'/domain/'learned_confirmation.jsonl.gz'
  if learned.exists() and (HERE/'scores'/domain/'learned_summary.json').exists():
   for m in ['residual','binary','full_replayed']:assert rows(learned,m)==old,(domain,m)
   report['learned_matches_headline']=True
   from score_controls import scores
   previous=scores(ARCHIVE/'runs'/run/'records.jsonl.gz',[method])[method]
   replay=json.loads((HERE/'scores'/domain/'learned_summary.json').read_text())['full_replayed']
   error=max(abs(replay[k]-v) for k,v in previous.items() if v is not None)
   assert error<1e-6,(domain,error)
   report['full_replay_max_absolute_nrmse_difference']=error
  reports[domain]=report
 (HERE/'alignment_checks.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports))
if __name__=='__main__':main()
