"""The one explicit attempt identity used by supervisor and scientific stages."""
import json,hashlib,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];CODE=Path(__file__).resolve().parent
CONFIG=CODE/'ATTEMPT.json'
SETTINGS=json.loads(CONFIG.read_text())
OUT=ROOT/SETTINGS['results'];DOC=ROOT/SETTINGS['docs'];OLD=ROOT/SETTINGS['previous_results']
ATTEMPT=SETTINGS['attempt_id']
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atomic_json(p,data):
 p=Path(p)
 if p.exists():raise FileExistsError(p)
 tmp=p.with_suffix(p.suffix+'.pending')
 with tmp.open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def accounting():
 for p,h in SETTINGS['prior_accounting_hashes'].items():
  if sha(ROOT/p)!=h:raise ValueError('prior ledger changed')
 rows=[json.loads(s) for s in (OUT/'RESOURCE_LEDGER.jsonl').read_text().splitlines()] if (OUT/'RESOURCE_LEDGER.jsonl').exists() else []
 return SETTINGS['prior_debit_cpu_seconds']+sum(r['charged_cpu_seconds'] for r in rows),sum(r['charged_cpu_seconds'] for r in rows if r['phase']=='engineering'),rows
