"""Join every FEM geometry to original validated fine/coarse/wide CPU work."""
import csv,json
from common import *
from pdkcap.reference_dataset import components
out=ROOT/'results/dac_characterization_20261114';sr=Path(PATHS['solver_root']);rows=[];receipts=[]
for design,run,dataset in [('reference_design_v2','reference_full_v2','reference_dataset_v2'),('round2_design_v2','round2_full_v1','round2_reference_dataset_v1'),('round3_design_v1','round3_full_v1','round3_reference_dataset_v1')]:
    grid=sr/'runs'/design/'grid.json';ledger=sr/'runs'/run/'ledger.jsonl';summary=json.loads((ledger.parent/'summary.json').read_text());assert summary['all_requested_passed'] and summary['grid_sha256']==sha(grid)
    entries={r['id']:r for r in map(json.loads,ledger.open())}
    tt=read_tables(ROOT/f'runs/{dataset}/tables.jsonl');lookup={(t['table_id'],tuple(x)):np.asarray(y) for t in tt for x,y in zip(t['coordinates'],t['labels'])}
    for g in json.loads(grid.read_text()):
        m=g['spec']['metadata'];coord=(m['width_um'],m['distance_um'],m['lateral_spacing_um']);fine=entries[g['id']+'-fine']['result'];computed=components(fine['matrix_F_per_m'],m)
        assert np.array_equal(computed,lookup[(g['reference_id'],coord)])
        row=dict(dataset=dataset,table_id=g['reference_id'],geometry_id=g['id'],coordinates=json.dumps(coord),ledger_path=str(ledger),ledger_sha256=sha(ledger) if False else '',fine_cpu_seconds=fine['cpu_seconds'],fine_recorded_wall_seconds=fine['wall_seconds'],fine_excitations=len(fine['matrix_F_per_m']),validated_cpu_seconds=sum(entries[g['id']+'-'+l]['result']['cpu_seconds'] for l in ('coarse','fine','wide')),validated_excitations=sum(len(entries[g['id']+'-'+l]['result']['matrix_F_per_m']) for l in ('coarse','fine','wide')),fine_id=g['id']+'-fine',coarse_id=g['id']+'-coarse',wide_id=g['id']+'-wide',cost_kind='recorded-cost replay')
        rows.append(row)
    h=sha(ledger)
    for r in rows:
        if r['dataset']==dataset:r['ledger_sha256']=h
    receipts.append(dict(dataset=dataset,grid_sha256=sha(grid),ledger_sha256=h,summary_sha256=sha(ledger.parent/'summary.json'),labels_exact=True))
with (out/'geometry_cost_index.csv').open('x') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
write(out/'geometry_cost_verification.json',dict(geometries=len(rows),receipts=receipts,new_solver_runs=0,zero_charged_wall_not_used=True))
print('verified geometries',len(rows))
