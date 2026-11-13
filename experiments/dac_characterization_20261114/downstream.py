"""Budget completion -> exact native rule export -> fixed-layout OpenRCX/STA.
No routing, library, R, or constraint changes. Exclusive outputs, resume via
provenance checks; all failed subprocess logs retained.
"""
import os,json,time,subprocess,argparse,collections,csv,re
from common import *
from evaluate import Predictors,population,trajectory
sys.path.insert(0,str(ROOT/'scripts'))
from downstream_holdout_predict import study_key,upstream_key
from downstream_holdout_export import SOURCES
from openrcbench.io import read_jsonl
from openrcbench.export import export_openrcx
from openrcbench.spef import compare_spef
R=ROOT/'results/dac_characterization_20261114/downstream'
UP=Path(PATHS['upstream_root']);FLOW=UP/'tools/OpenROAD-flow-scripts/flow'
PLAN=json.loads((HERE/'EXPERIMENT_PLAN.yaml').read_text())['downstream']
CASES=json.loads((ROOT/'database/sta_cases.json').read_text())

def export():
    out=R/'rules';out.mkdir(parents=True,exist_ok=False)
    ts=read_tables(ROOT/'runs/public_inventory_holdout_v1/tables.jsonl');held=[t for t in ts if t['partition']=='holdout'];assert len(held)==84
    index={study_key(t):t for t in held};ds=read_jsonl(UP/'data/processed/dataset.jsonl');pairs=[]
    for u in ds:
        if upstream_key(u) in index:pairs.append((u,index[upstream_key(u)]))
    assert len(pairs)==84
    excluded=[t['table_id'] for u,t in pairs if len(t['coordinates'])<4]
    pairs=[(u,t) for u,t in pairs if len(t['coordinates'])>=4]
    p=Predictors('public',json.loads((HERE/'selected_public.json').read_text()),learned=False)
    manifest=[];support=[];start=time.perf_counter()
    for b in PLAN['budgets']:
        for seed in PLAN['seeds']:
            payload={m:{'tables':{}} for m in PLAN['methods']}
            for u,t in pairs:
                c,q,init=population(t,seed);actual=min(b,len(c));_,_,snap=trajectory(t,seed,'farthest',[actual]);o,v,_,_=snap[-1]
                support.append(dict(table_id=t['table_id'],upstream_id=u.table_id,budget_requested=b,budget_actual=len(o),seed=seed,support=o.tolist(),query=q.tolist(),candidates=c.tolist()))
                for m in payload:
                    pred=p(m,public_input(t),o,v);hidden=np.setdiff1d(np.arange(len(pred)),o)
                    # Do not rewrite observed rows: byte-level exact retention.
                    payload[m]['tables'][u.table_id]={str(i):{name:float(pred[i,j]) for j,name in enumerate(t['target_names'])} for i in hidden}
            for m,values in payload.items():
                name=f'{m}_B{b}_s{seed}';path=out/f'{name}.json';write(path,values)
                for platform,source_id,rel in SOURCES:
                    folder=out/platform;folder.mkdir(exist_ok=True);original=UP/'data/raw'/rel;dest=folder/f'{name}.rules'
                    t0=time.perf_counter();receipt=export_openrcx(original,UP/'data/processed/dataset.jsonl',path,dest,source_id=source_id)
                    manifest.append(dict(name=name,method=m,budget=b,seed=seed,platform=platform,path=str(dest),sha256=sha(dest),original=str(original),original_sha256=sha(original),export_seconds=time.perf_counter()-t0,**receipt))
    write(out/'manifest.json',dict(exports=manifest,support=support,elapsed_seconds=time.perf_counter()-start,scope='eligible subset of original 84 held-out tables; full grid completion; fixed Q',excluded_short_tables=excluded,eligible_tables=len(pairs),input_manifest_sha256=sha(HERE/'MANIFEST.json')))
    print('native exports',len(manifest),flush=True)

def native(case,variant,rules):
    platform,design=case.split('/');info=CASES[case];out=R/'native'/platform/design/variant;out.mkdir(parents=True,exist_ok=False)
    exe=UP/'tools/openroad-install-20260909/bin/openroad'
    env=dict(os.environ,STA_FLOW=str(FLOW),STA_PLATFORM=platform,STA_LIBS=' '.join('{'+str(FLOW/n)+'}' for n in info['libraries']),STA_ODB=str(ROOT/info['odb']),STA_SDC=str(ROOT/info['sdc']),STA_SPEF=str(out/'extracted.spef'),STA_OUT=str(out),DAC_RULES=str(rules))
    ld=UP/'tools/openroad-deps-20260908';env['LD_LIBRARY_PATH']=f'{ld}/lib64:{ld}/lib:'+env.get('LD_LIBRARY_PATH','')
    provenance=dict(odb=sha(env['STA_ODB']),sdc=sha(env['STA_SDC']),rules=sha(rules),openroad=sha(exe),libs={n:sha(FLOW/n) for n in info['libraries']},tcl=sha(HERE/'native.tcl'))
    write(out/'FROZEN.json',dict(case=case,variant=variant,provenance=provenance,threads=1))
    start=time.perf_counter()
    with (out/'native.log').open('x') as f:
        try:r=subprocess.run([str(exe),'-threads','1','-exit',str(HERE/'native.tcl')],env=env,cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        except subprocess.TimeoutExpired:r=None
    if r is None or r.returncode:
        result=dict(status='failed',exit_code=None if r is None else r.returncode,wall_seconds=time.perf_counter()-start)
    else:
        raw=(out/'native.log').read_text();assert 'STA_EXPORT_COMPLETE' in raw
        ref=ROOT/CASES[case]['variants']['golden']['spef'] if variant=='golden' else R/'native'/platform/design/'golden/extracted.spef'
        compare=compare_spef(ref,out/'extracted.spef',out/'comparison.json')
        assert compare['common_nets']==compare['golden_nets']==compare['candidate_nets']
        if variant=='golden':assert all(compare['metrics'][k]['rmse']==0 for k in ('capacitance','resistance'))
        else:assert compare['metrics']['resistance']['rmse']==0
        result=dict(status='ok',wall_seconds=time.perf_counter()-start,extraction_seconds=float(re.search(r'DAC_EXTRACTION_SECONDS ([0-9.]+)',raw)[1]),worst_slack_native=float(re.search(r'worst slack max ([-.0-9]+)',raw)[1]),tns_native=float(re.search(r'tns max ([-.0-9]+)',raw)[1]),comparison=compare,spef_sha256=sha(out/'extracted.spef'))
    write(out/'COMPLETED.json',result);print(case,variant,result['status'],flush=True);return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--export',action='store_true');ap.add_argument('--pilot',action='store_true');ap.add_argument('--case');a=ap.parse_args()
    if a.export:export();return
    manifest=json.loads((R/'rules/manifest.json').read_text())
    for case in ([a.case] if a.case else list(CASES)):
        platform=case.split('/')[0];entries=[e for e in manifest['exports'] if e['platform']==platform]
        golden=R/'native'/case/'golden/COMPLETED.json'
        if golden.exists():assert json.loads(golden.read_text())['status']=='ok'
        else:
            r=native(case,'golden',Path(entries[0]['original']))
            if r['status']!='ok':continue
        if a.pilot:continue
        for e in entries:
            out=R/'native'/case/e['name']/'COMPLETED.json'
            if out.exists():
                assert json.loads((out.parent/'FROZEN.json').read_text())['provenance']['rules']==e['sha256'];continue
            assert sha(e['path'])==e['sha256'];native(case,e['name'],Path(e['path']))
if __name__=='__main__':main()
