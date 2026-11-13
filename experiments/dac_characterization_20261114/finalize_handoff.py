"""Finish a native receipt after administrative queue handoff, without rerun."""
import os,signal,json,time,re
from common import *
from downstream import R,CASES
from openrcbench.spef import compare_spef
h=json.loads((R/'queue_handoff.json').read_text());parent=h['parent_pid']
for pid in h['child_pids']:
 p=Path(f'/proc/{pid}/stat')
 if p.exists():assert p.read_text().split(') ',1)[1].split()[0]=='Z','OpenROAD child still running; do not terminate parent'
partials=[p.parent for p in (R/'native').glob('*/*/*/FROZEN.json') if not (p.parent/'COMPLETED.json').exists()]
for out in partials:
 frozen=json.loads((out/'FROZEN.json').read_text());case=frozen['case'];variant=frozen['variant'];raw=(out/'native.log').read_text();assert 'STA_EXPORT_COMPLETE' in raw
 ref=ROOT/CASES[case]['variants']['golden']['spef'] if variant=='golden' else R/'native'/case/'golden/extracted.spef'
 compare=compare_spef(ref,out/'extracted.spef',out/'comparison.json');assert compare['common_nets']==compare['golden_nets']==compare['candidate_nets'];assert compare['metrics']['resistance']['rmse']==0
 if variant=='golden':assert compare['metrics']['capacitance']['rmse']==0
 result=dict(status='ok',wall_seconds=(out/'native.log').stat().st_mtime-(out/'FROZEN.json').stat().st_mtime,wall_measurement='reconstructed from log/FROZEN timestamps after administrative queue handoff',extraction_seconds=float(re.search(r'DAC_EXTRACTION_SECONDS ([0-9.]+)',raw)[1]),worst_slack_native=float(re.search(r'worst slack max ([-.0-9]+)',raw)[1]),tns_native=float(re.search(r'tns max ([-.0-9]+)',raw)[1]),comparison=compare,spef_sha256=sha(out/'extracted.spef'))
 write(out/'COMPLETED.json',result)
os.kill(parent,signal.SIGTERM);os.kill(parent,signal.SIGCONT)
write(R/'queue_handoff_completed.json',dict(completed_unix=time.time(),finalized=[str(p) for p in partials],parent_stopped=True,openroad_children_completed_without_termination=True))
print('finalized without rerun',partials)
