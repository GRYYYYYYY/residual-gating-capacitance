import json,hashlib,csv
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'results/layout_offgrid_20261115';U=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
contracts=[]
for path in sorted((O/'native').glob('*/*/receipt.json')):
 r=json.loads(path.read_text());proc,design=r['case'].split('/')
 lefs=list((U/'tools/OpenROAD-flow-scripts/flow/platforms'/proc).rglob('*.lef'))
 ctf=R/f'.cache/AttentionCap/pattern_gen/itf_lib/{proc}.ctf'
 contracts.append(dict(process=proc,corner='typ',design=design,layout=dict(path=r['odb_path'],sha256=r['odb_sha256']),rules=dict(path=r['rules_path'],sha256=r['rules_sha256']),lef_sources=[dict(path=str(p),sha256=sha(p)) for p in lefs],lef_odb_equivalence='not independently reimported; ODB tech is runtime authority',ctf=dict(path=str(ctf),sha256=sha(ctf)) if ctf.exists() else None,material_match=False,reason='Native calibration stack, effective width bias, ground definition and per-pair versus summed lateral projection not jointly established. Ordinary LEF is not a complete electrostatic stack.',native_mapping='NATIVE_PATTERN_INSTANCE only for uniquely resolved rule keys',direct_reference_mapping='LAYOUT_PARAMETERIZED_TEMPLATE for ASAP7 M4/M5 adjacent contexts; unsupported otherwise',native_projection='pre-assembly coupling_ and fringe_; native units before scaling/threshold/net merging',FEM_projection='sum of two lateral couplings; external ground plus explicit context electrodes; diagonal separate; F/m',FEM_boundary='all outside edges and finite context electrodes grounded; infinite extrusion; er=1 above last CTF dielectric',exact_layout_section_verified=False,source_layout_drc='existing routed DRC=0 recorded in upstream frozen downstream summary; no new foundry DRC',online_replacement=False))
(O/'physical_contracts.json').write_text(json.dumps(contracts,indent=2))
