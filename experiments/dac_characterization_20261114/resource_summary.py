"""Separate measured work from unknown costs; never invent a total speedup."""
import csv,json,gzip
from common import *
R=ROOT/'results/dac_characterization_20261114';S=R/'summary'
train=list(csv.DictReader((S/'training_cost.csv').open()))
native=list(csv.DictReader((S/'native_cost.csv').open()))
new=[r for r in train if r['kind'].startswith('new')]
rows=[json.loads(l) for s in MODELS for l in gzip.open(R/f'confirmation_{s}/records.jsonl.gz','rt')]
outputs=[p for p in R.rglob('*') if p.is_file()]
d=dict(new_source_training_runs=len(new),new_source_training_measured_cpu_seconds=sum(float(r['cpu_seconds']) for r in new if r['cpu_seconds']),new_source_training_runs_without_cpu=sum(not r['cpu_seconds'] for r in new),new_source_training_sum_wall_seconds=sum(float(r['wall_seconds']) for r in new if r['wall_seconds']),main_confirmation_measured_prediction_adaptation_cpu_seconds=sum(r.get('prediction_and_adaptation_cpu_seconds',0.) for r in rows),failed_fork_cpu_seconds=770.07,native_invocations=len(native),native_sum_wall_seconds=sum(float(r['wall_seconds']) for r in native),native_sum_extraction_seconds=sum(float(r['extraction_seconds']) for r in native),native_cpu_seconds=None,export_manifest=json.loads((R/'downstream/rules/manifest.json').read_text())['elapsed_seconds'],artifact_bytes=sum(p.stat().st_size for p in outputs),new_GPU_hours=0,new_field_solver_invocations=0,observed_max_heavy_job_concurrency=4,unknown_costs=['historical source/pretraining CPU/GPU totals','new source validation selection CPU','AttentionCap/reverse target adaptation CPU','native CPU','initial support population setup outside profiles'],accounting='CPU and sum of individual walls reported separately; parallel walls are not end-to-end elapsed; costs are incomplete, no amortized superiority claim')
assert d['new_source_training_runs']==36 and d['native_invocations']==248
assert d['artifact_bytes']<15_000_000_000
(S/'resource_usage_summary.json').write_text(json.dumps(d,indent=2));print(d)
