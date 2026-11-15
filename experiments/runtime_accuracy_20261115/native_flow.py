"""Repeat fixed-node rule export and release PEX/STA; no new rule nodes."""
from common_runtime import *
import argparse,re,collections
import numpy as np
from common import public_input
from evaluate import Predictors,trajectory
from downstream import study_key,upstream_key,SOURCES,CASES,FLOW
from openrcbench.io import read_jsonl
from openrcbench.export import export_openrcx
from openrcbench.spef import compare_spef

def prepare():
    pin();start=stamp();z=stamp()
    ts=[t for t in map(json.loads,(R/'runs/public_inventory_holdout_v1/tables.jsonl').read_text().splitlines()) if t['partition']=='holdout']
    index={study_key(t):t for t in ts};pairs=[]
    for u in read_jsonl(UP/'data/processed/dataset.jsonl'):
        if upstream_key(u) in index and len(index[upstream_key(u)]['coordinates'])>=4:pairs.append((u,index[upstream_key(u)]))
    data_load=elapsed(z);assert len(pairs)==83
    z=stamp();p=Predictors('public',read(R/'experiments/dac_characterization_20261114/selected_public.json'),learned=False);load_cost=elapsed(z)
    z=stamp();supports=[]
    for u,t in pairs:
        _,_,snaps=trajectory(t,11,'farthest',[min(8,len(t['coordinates'])-max(1,round(.2*len(t['coordinates']))))]);o,v,_,_=snaps[-1];supports.append((u,t,o,v))
    support_cost=elapsed(z);dest=O/'rules';dest.mkdir(exist_ok=True);rows=[]
    old=read(R/'results/dac_characterization_20261114/downstream/rules/manifest.json')['exports']
    for m in ['cmi','binary','full']:
        z=stamp();payload={'tables':{}}
        for u,t,o,v in supports:
            pred=p(m,public_input(t),o,v);hidden=np.setdiff1d(np.arange(len(pred)),o)
            payload['tables'][u.table_id]={str(i):{name:float(pred[i,j]) for j,name in enumerate(t['target_names'])} for i in hidden}
        prediction=elapsed(z);z=stamp();path=dest/f'{m}_B8_s11.json';write(path,payload);payload_write=elapsed(z)
        for platform,sid,rel in SOURCES:
            z=stamp();output=dest/f'{platform}_{m}_B8_s11.rules';original=UP/'data/raw'/rel
            receipt=export_openrcx(original,UP/'data/processed/dataset.jsonl',path,output,source_id=sid);export=elapsed(z)
            prior=next(r for r in old if r['platform']==platform and r['name']==f'{m}_B8_s11')
            assert sha(output)==prior['sha256'],(platform,m,'export changed')
            rows.append(dict(platform=platform,method=m,rule_path=str(output),rule_sha256=sha(output),bytes=output.stat().st_size,original=str(original),original_sha256=sha(original),original_bytes=original.stat().st_size,prediction_all_platforms=prediction,export=export,payload_write=payload_write,equal_frozen_export=True,receipt=receipt))
    write(O/'rule_preparation.json',dict(data_load=data_load,shared_model_bundle_load=load_cost,support_selection=support_cost,rows=rows,total=elapsed(start),scope='B8 seed11; 83 eligible source-held-out tables; same nodes and R; no node enrichment. Prediction timing spans all four processes; load and support selection shared and counted once. Full/control weights bundled by existing loader.',peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    print('prepared identical rules',len(rows),flush=True)

def native():
    pin();pre=read(O/'rule_preparation.json');exe=UP/'tools/openroad-install-20260909/bin/openroad';rows=[];rng=np.random.default_rng(20261115)
    tasks=[(case,m) for case in sorted(CASES) for m in ['original','cmi','binary','full']]
    assert len(tasks)==32
    # Three randomized complete passes; cold process each run, OS cache uncontrolled.
    for block in range(3):
        for idx in rng.permutation(len(tasks)):
            case,m=tasks[idx];platform,design=case.split('/');info=CASES[case];out=O/'native'/platform/design/m/str(block);out.mkdir(parents=True,exist_ok=True)
            entry=next(e for e in pre['rows'] if e['platform']==platform and e['method']==('cmi' if m=='original' else m))
            rules=Path(entry['original'] if m=='original' else entry['rule_path'])
            env=dict(os.environ,STA_FLOW=str(FLOW),STA_PLATFORM=platform,STA_LIBS=' '.join('{'+str(FLOW/n)+'}' for n in info['libraries']),STA_ODB=str(R/info['odb']),STA_SDC=str(R/info['sdc']),STA_SPEF=str(out/'extracted.spef'),DAC_RULES=str(rules))
            ld=UP/'tools/openroad-deps-20260908';env['LD_LIBRARY_PATH']=f'{ld}/lib64:{ld}/lib:'+env.get('LD_LIBRARY_PATH','')
            before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.perf_counter()
            with (out/'native.log').open('w') as f:
                proc=subprocess.run(['/usr/bin/time','-v','-o',str(out/'resource.txt'),str(exe),'-threads','1','-exit',str(H/'native_flow.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
            wall=time.perf_counter()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN);log=(out/'native.log').read_text();assert proc.returncode==0 and 'RUNTIME_COMPLETE' in log,(case,m,block)
            stages={n+'_s':float(v) for n,v in re.findall(r'RUNTIME_STAGE (\S+) (\S+)',log)}
            mem={n+'_rss_kib':int(v) for n,v in re.findall(r'RUNTIME_RSS (\S+) (\d+)',log)}
            peak=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',(out/'resource.txt').read_text())[1])
            # Existing golden SPEF is the same immutable routed/corner reference.
            comp=compare_spef(R/'results/dac_characterization_20261114/downstream/native'/platform/design/'golden/extracted.spef',out/'extracted.spef',out/'comparison.json')
            assert comp['common_nets']==comp['golden_nets']==comp['candidate_nets']
            def electrical_hash(path):
                text=Path(path).read_bytes();pos=text.index(b'*D_NET');return hashlib.sha256(text[pos:]).hexdigest()
            frozen_variant='golden' if m=='original' else f'{m}_B8_s11'
            frozen_spef=R/'results/dac_characterization_20261114/downstream/native'/platform/design/frozen_variant/'extracted.spef'
            electrical=electrical_hash(out/'extracted.spef');assert electrical==electrical_hash(frozen_spef),(case,m,'electrical SPEF changed')
            slack=re.search(r'worst slack(?: max)? (-?[\d.eE+]+)',log);tns=re.search(r'tns(?: max)? (-?[\d.eE+]+)',log)
            unit=re.search(r'^\s*time\s+([\d.]+)(\w+)',log,re.M);factor=float(unit[1])*{'s':1e12,'ms':1e9,'us':1e6,'ns':1e3,'ps':1.,'fs':1e-3}[unit[2]]
            assert slack and tns
            row=dict(case=case,method=m,block=block,wall_s=wall,cpu_s=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,peak_rss_kib=peak,rule_bytes=rules.stat().st_size,rule_sha256=sha(rules),openroad_sha256=sha(exe),odb_sha256=sha(env['STA_ODB']),spef_sha256=sha(out/'extracted.spef'),worst_slack=float(slack[1]) if slack else None,tns=float(tns[1]) if tns else None,**stages,**mem)
            row.update(sta_time_unit=unit[0].strip(),worst_slack_ps=float(slack[1])*factor,tns_ps=float(tns[1])*factor)
            write(out/'receipt.json',dict(**row,comparison=comp,electrical_sha256=electrical,identical_frozen_variant=True));rows.append(row);csvwrite(O/'native_flow_timing.csv',rows)
            # Keep raw SPEFs locally, not in the public repository.
            print('native',case,m,block,round(wall,3),flush=True)
    write(O/'native_flow_completed.json',dict(runs=len(rows),total_cpu_s=sum(r['cpu_s'] for r in rows),total_wall_s=sum(r['wall_s'] for r in rows),trace_enabled=False,rule_parse_scope='rule_registration is measured separately; deferred parse remains inside extract_parasitics, not falsely called isolated rule-load time',memory_scope='resident RSS before/after rule registration and extraction; peak process RSS; no attribution of all extraction allocation to rule tables',input_scope='8 fixed ODBs, original/CMI/Binary/Full B8 seed11 rules, 3 passes, same release OpenROAD/corner'))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','native']);a=ap.parse_args();prepare() if a.phase=='prepare' else native()
