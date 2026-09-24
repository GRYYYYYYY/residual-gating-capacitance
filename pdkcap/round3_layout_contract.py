"""Freeze named fixed-layout inputs before launching the reused ORFS audit."""
import json
from pathlib import Path
from .common import ROOT, file_hash
from .round2_downstream import FLOW, UPSTREAM, eda_environment


def capture(platform,design):
    golden=FLOW/'results'/platform/design/'golden_20260909'
    previous=ROOT/'runs/round2_downstream_v1'/platform/design/'golden.json'
    old=json.loads(previous.read_text())
    environment=eda_environment()
    hook=UPSTREAM/'scripts'/('time_extraction_gf180.tcl' if platform=='gf180' else 'time_extraction.tcl')
    inputs=[golden/'6_1_fill.odb',golden/'6_1_fill.sdc',golden/'6_final.spef',
        FLOW/'Makefile',FLOW/'designs'/platform/design/'config.mk',FLOW/'platforms'/platform/'config.mk',hook,
        Path(environment['OPENROAD_EXE']),Path(environment['OPENSTA_EXE'])]
    inputs += [UPSTREAM/'scripts'/name for name in ('time_extraction.tcl','skip_pdnsim_gf180.tcl','time_extraction_gf180.tcl')]
    inputs += [Path(path) for path in old['liberty_sha256']]
    if (golden/'memories').is_dir():inputs += [p for p in (golden/'memories').rglob('*') if p.is_file()]
    hashes={str(p.resolve()):file_hash(p) for p in inputs}
    return dict(platform=platform,design=design,input_hashes=hashes,
        previous_golden_receipt_sha256=file_hash(previous),
        liberty_sha256={path:file_hash(path) for path in old['liberty_sha256']},
        expected_provenance=dict(database_sha256=file_hash(golden/'6_1_fill.odb'),
            constraints_sha256=file_hash(golden/'6_1_fill.sdc'),openroad_sha256=file_hash(environment['OPENROAD_EXE']),
            timing_hook_sha256=file_hash(hook),num_cores=1),
        scope='named layout/SDC/golden SPEF/config/Makefile/tools/hooks/Liberty/memory inputs; not a complete OS image')


def verify_inputs(contract):
    for path,sha in contract['input_hashes'].items():
        if file_hash(path)!=sha:raise ValueError(f'layout input drift: {path}')


def verify_state(contract,state):
    if state['platform']!=contract['platform'] or state['design']!=contract['design']:
        raise ValueError('layout identity mismatch')
    for key,value in contract['expected_provenance'].items():
        if state['provenance'][key]!=value:raise ValueError(f'layout provenance mismatch: {key}')
    if state['liberty_sha256']!=contract['liberty_sha256']:
        raise ValueError('Liberty inputs differ from pre-run freeze')
