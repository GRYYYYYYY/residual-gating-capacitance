"""Strict capacitance-only export and isolated read-only-source ORFS audit."""
import argparse,gzip,json,os,re,shutil,signal,subprocess,sys,time
from pathlib import Path
import numpy as np
import torch
from .common import ROOT,read_tables,write_json,file_hash
from .budget import allocation
from .sampling import mask
from .round2_predict import Predictors

UPSTREAM=ROOT.parent/'openrcbench-v1'
FLOW=UPSTREAM/'tools/OpenROAD-flow-scripts/flow'
SOURCES=[
 ('asap7','orfs_asap7_20260903','asap7/rcx_patterns.rules'),
 ('gf180','orfs_gf180_20260903:gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules','gf180/gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules'),
 ('ihp-sg13g2','orfs_ihp_sg13g2_20260903','ihp_sg13g2/IHP_rcx_patterns.rules'),
 ('sky130hs','orfs_sky130hs_20260903','sky130/rcx_patterns.rules')]


def external_imports():
    if str(UPSTREAM) not in sys.path:sys.path.append(str(UPSTREAM))
    from openrcbench.export import export_openrcx
    from openrcbench.spef import compare_spef
    from openrcbench.openrcx import parse_openrcx
    return export_openrcx,compare_spef,parse_openrcx


def export_rules(bundle_path,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(1)
    export_openrcx,_,parse_openrcx=external_imports()
    raw=UPSTREAM/'data/processed/dataset.jsonl';raw_tables={t['table_id']:t for t in read_tables(raw)}
    public_path=ROOT/'runs/public_inventory_v1/tables.jsonl';public=read_tables(public_path)
    bundle=json.loads(Path(bundle_path).read_text());predictor=Predictors(bundle)
    methods=('linear','pchip','original_dro','gated','selected_hard');exports=[];goldens=[]
    for platform,source_id,relative in SOURCES:
        original=UPSTREAM/'data/raw'/relative;folder=output/platform;folder.mkdir()
        golden=folder/'golden.rules';shutil.copy2(original,golden)
        source_tables=[t for t in raw_tables.values() if t['source_id']==source_id]
        source_rows=sum(len(t['rows']) for t in source_tables)
        if not source_tables:raise ValueError('missing exact source identity')
        goldens.append(dict(platform=platform,path=str(golden.resolve()),sha256=file_hash(golden),original=str(original.resolve()),source_id=source_id))
        selected=[t for t in public if t['partition']=='test' and t['source_id']==source_id]
        if not selected:raise ValueError('no PDKCap test tables for downstream source')
        for ratio in (.3,.5):
            for seed in (11,29,47):
                payloads={m:{'tables':{}} for m in methods};hidden_ids=[]
                for t in selected:
                    x=np.asarray(t['coordinates']);y=np.asarray(t['labels']);o,q=mask(x,'block',ratio,seed)
                    predictions=predictor.all(t,o,y[o],methods)
                    # PDKCap regrouping preserves source identity but changes table ids.
                    mapping={}
                    for sid in t['source_table_ids']:
                        source=raw_tables[sid]
                        if source['source_id']!=source_id:raise ValueError('cross-source identity merge')
                        for index,row in enumerate(source['rows']):
                            coord=(source['width'],row['spacing_left'],row['spacing_right'])
                            mapping.setdefault(coord,[]).append((sid,index,row))
                    for i in q:
                        key=tuple(x[i]);matches=mapping.get(key,[])
                        if not matches:raise ValueError('hidden coordinate has no original row')
                        for sid,index,row in matches:
                            np.testing.assert_array_equal(y[i],[row['coupling_cap'],row['ground_cap']])
                            hidden_ids.append((sid,index))
                            for method in methods:
                                value=predictions[method]['prediction'][i]
                                payloads[method]['tables'].setdefault(sid,{})[str(index)]={k:float(v) for k,v in zip(('coupling_cap','ground_cap'),value)}
                if len(hidden_ids)!=len(set(hidden_ids)):raise ValueError('duplicate export ownership')
                for method in methods:
                    name=f'{method}_block{int(ratio*100)}_mask{seed}';predfile=folder/f'{name}.json'
                    write_json(predfile,payloads[method]);out=folder/f'{name}.rules'
                    result=export_openrcx(original,raw,predfile,out,source_id=source_id)
                    exemplar=source_tables[0]
                    parsed={t.table_id:t for t in parse_openrcx(out,source_id=source_id,process_id=exemplar['process_id'],corner_id=exemplar['corner_id'])}
                    if set(parsed)!={t['table_id'] for t in source_tables}:raise ValueError('export table set changed')
                    actual=0
                    for source in source_tables:
                        for i,(before,after) in enumerate(zip(source['rows'],parsed[source['table_id']].rows)):
                            changes=payloads[method]['tables'].get(source['table_id'],{}).get(str(i),{})
                            for field,value in before.items():
                                if field not in changes and after[field]!=value:raise ValueError('unmasked field or resistance changed')
                            actual+=int(any(after[k]!=before[k] for k in ('coupling_cap','ground_cap')))
                    exports.append(dict(platform=platform,method=method,ratio=ratio,mask_seed=seed,path=str(out.resolve()),sha256=file_hash(out),
                        predictions_sha256=file_hash(predfile),source_id=source_id,source_rows=source_rows,test_tables=len(selected),
                        masked_rows=len(hidden_ids),changed_numeric_rows=actual,changed_numeric_row_fraction=actual/source_rows,**result))
    write_json(output/'manifest.json',dict(bundle_sha256=file_hash(bundle_path),public_sha256=file_hash(public_path),raw_sha256=file_hash(raw),
        exporter_sha256=file_hash(__file__),upstream_exporter_sha256=file_hash(UPSTREAM/'openrcbench/export.py'),
        methods=list(methods),goldens=goldens,exports=exports,scope='PDKCap held-out capacitance fields only; exact original R preserved'))


def eda_environment():
    env=dict(os.environ);tools=UPSTREAM/'tools'
    env.update(OPENROAD_EXE=str(tools/'openroad-install-20260909/bin/openroad'),
        OPENSTA_EXE=str(tools/'openroad-install-20260909/bin/sta'),YOSYS_EXE=str(tools/'yosys-install-20260909/bin/yosys'),
        PYTHON_EXE=str(UPSTREAM/'.venv-eda/bin/python'),NUM_CORES='1',QT_QPA_PLATFORM='offscreen',
        OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    env['PATH']=':'.join(str(tools/p) for p in ('openroad-deps-20260908/bin','openroad-install-20260909/bin','yosys-install-20260909/bin'))+':'+env['PATH']
    env['LD_LIBRARY_PATH']=':'.join(str(tools/p) for p in ('openroad-deps-20260908/lib64','openroad-deps-20260908/lib'))+':'+env.get('LD_LIBRARY_PATH','')
    return env


def liberty_units(log):
    files={};units=set()
    for line in Path(log).read_text().splitlines():
        if not line.startswith('read_liberty '):continue
        p=Path(line.split()[-1]);p=p if p.is_absolute() else FLOW/p
        opener=gzip.open if p.suffix=='.gz' else open
        with opener(p,'rt') as f:header=f.read(131072)
        match=re.search(r'time_unit\s*:\s*"?([0-9.eE+-]+)\s*(s|ms|us|ns|ps|fs)"?\s*;',header)
        if not match:raise ValueError(f'missing Liberty units {p}')
        factor=float(match[1])*dict(s=1e9,ms=1e6,us=1e3,ns=1,ps=1e-3,fs=1e-6)[match[2]]
        units.add(factor);files[str(p.resolve())]=file_hash(p)
    if len(units)!=1:raise ValueError('nonuniform or missing timing units')
    return units.pop(),files


def audit_case(platform,design,variants,output):
    _,compare_spef,_=external_imports();output=Path(output);output.mkdir(parents=True,exist_ok=False)
    env=eda_environment();work=(output/'flow').resolve();work.mkdir()
    golden=FLOW/'results'/platform/design/'golden_20260909';snapshot=golden/'6_1_fill.odb';constraints=golden/'6_1_fill.sdc'
    if not all(p.is_file() for p in (snapshot,constraints,golden/'6_final.spef')):raise ValueError('incomplete golden inputs')
    for dirname in ('time_extraction.tcl','skip_pdnsim_gf180.tcl','time_extraction_gf180.tcl'):
        shutil.copy2(UPSTREAM/'scripts'/dirname,output/dirname)
    hook=(output/('time_extraction_gf180.tcl' if platform=='gf180' else 'time_extraction.tcl')).resolve()
    reference=None;states=[]
    for variant in variants:
        name=variant.get('name') or ('golden' if variant['method']=='golden' else f"{variant['method']}_block{int(variant['ratio']*100)}_mask{variant['mask_seed']}")
        rules=Path(variant['path']).resolve()
        if file_hash(rules)!=variant['sha256']:raise ValueError('rule hash mismatch')
        target=work/'results'/platform/design/name;target.mkdir(parents=True)
        shutil.copy2(snapshot,target/snapshot.name);shutil.copy2(constraints,target/constraints.name)
        if (golden/'memories').is_dir():shutil.copytree(golden/'memories',target/'memories')
        command=['make','--no-print-directory','-C',str(FLOW),f'DESIGN_CONFIG=designs/{platform}/{design}/config.mk',
                 f'FLOW_VARIANT={name}',f'WORK_HOME={work}',f'RCX_RULES={rules}',f'PRE_FINAL_REPORT_TCL={hook}','NUM_CORES=1']
        if platform=='gf180':command.append('CORNER=TC')
        probe='.PHONY: pdkcap-path-check\npdkcap-path-check:\n\t@printf "%s\\n" "$(RESULTS_DIR)" "$(LOG_DIR)" "$(REPORTS_DIR)" "$(OBJECTS_DIR)" "$(RCX_RULES)"\n'
        paths=subprocess.check_output(command+['-s','--eval='+probe,'pdkcap-path-check'],env=env,text=True).strip().splitlines()
        if len(paths)!=5 or Path(paths[-1])!=rules or not all(Path(p).resolve().is_relative_to(work) for p in paths[:4]):
            raise ValueError('ORFS write paths are not isolated inside current run')
        log=output/f'{name}.log';started=time.perf_counter()
        with allocation('training',f'round2 downstream {platform}/{design}/{name}',900):
            with log.open('x') as f:
                child=subprocess.Popen(command+['do-6_report'],stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
                try:
                    code=child.wait(timeout=880)
                    if code:raise RuntimeError(f'ORFS failed with {code}; inspect {log}')
                finally:
                    if child.poll() is None:
                        os.killpg(child.pid,signal.SIGTERM)
                        try:child.wait(timeout=5)
                        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        spef=target/'6_final.spef'
        if not spef.is_file():raise ValueError('missing candidate SPEF')
        if name=='golden':
            reference=spef
            replay=compare_spef(golden/'6_final.spef',spef,output/'golden_replay.json')
            if len({replay[k] for k in ('common_nets','golden_nets','candidate_nets')})!=1 or any(replay['metrics'][t]['rmse']!=0 for t in ('capacitance','resistance')):
                raise ValueError('golden replay not exactly RC-identical')
        if reference is None:raise ValueError('golden must precede candidates')
        comparison=compare_spef(reference,spef,output/f'{name}_spef.json')
        if len({comparison[k] for k in ('common_nets','golden_nets','candidate_nets')})!=1:raise ValueError('network set mismatch')
        if comparison['metrics']['resistance']['rmse']!=0:raise ValueError('capacitance-only export changed net resistance')
        factor,liberties=liberty_units(log);metrics=json.loads((work/'logs'/platform/design/name/'6_report.json').read_text())
        ws=metrics['finish__timing__setup__ws']*factor;tns=metrics['finish__timing__setup__tns']*factor
        text=log.read_text();timings=re.findall(r'OPENRCBENCH_EXTRACTION_SECONDS ([0-9.]+)',text)
        if len(timings)!=1:raise ValueError('missing extraction time evidence')
        state=dict(platform=platform,design=design,name=name,variant=variant,comparison=comparison,
            ws_ns=ws,wns_ns=min(0,ws),tns_ns=tns,liberty_to_ns=factor,liberty_sha256=liberties,
            spef=str(spef),spef_sha256=file_hash(spef),wall_seconds=time.perf_counter()-started,extraction_seconds=float(timings[0]),
            provenance=dict(database_sha256=file_hash(snapshot),constraints_sha256=file_hash(constraints),rules_sha256=file_hash(rules),
                            openroad_sha256=file_hash(env['OPENROAD_EXE']),timing_hook_sha256=file_hash(hook),num_cores=1),
            resolved_paths=paths,timing_metrics=metrics)
        write_json(output/f'{name}.json',state);states.append(state)
        print(json.dumps(dict(platform=platform,design=design,name=name,cap_nrmse=comparison['metrics']['capacitance']['nrmse'],ws_ns=ws)),flush=True)
    write_json(output/'COMPLETED.json',dict(states=len(states),scope='fixed-layout extraction/STA fidelity only',
        state_hashes={s['name']:file_hash(output/f"{s['name']}.json") for s in states}))


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('export');e.add_argument('--bundle',type=Path,required=True);e.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('audit');a.add_argument('--manifest',type=Path,required=True);a.add_argument('--platform',required=True);a.add_argument('--design',required=True)
    a.add_argument('--output',type=Path,required=True);a.add_argument('--golden-only',action='store_true')
    args=p.parse_args()
    if args.command=='export':
        with allocation('training','round2 downstream export '+str(args.output),3600):export_rules(args.bundle,args.output)
    else:
        manifest=json.loads(args.manifest.read_text());golden=next(g for g in manifest['goldens'] if g['platform']==args.platform)
        variants=[dict(golden,method='golden')]
        if not args.golden_only:variants += [v for v in manifest['exports'] if v['platform']==args.platform]
        audit_case(args.platform,args.design,variants,args.output)

if __name__=='__main__':main()
