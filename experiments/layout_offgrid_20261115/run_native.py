import os,json,subprocess,time,resource,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent;O=R/'results/layout_offgrid_20261115'
U=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026');D=U/'tools/openroad-deps-20260908'
exe=O/'build/openroad-trace';original=U/'tools/openroad-install-20260909/bin/openroad'
rules={'asap7':'asap7/rcx_patterns.rules','gf180':'gf180/gf180mcu_1p5m_1tm_9k_sp_smim_OPTB_typ.rules','ihp-sg13g2':'ihp_sg13g2/IHP_rcx_patterns.rules','sky130hs':'sky130/rcx_patterns.rules'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for case,info in json.loads((R/'database/sta_cases.json').read_text()).items():
 out=O/'native'/case;out.mkdir(parents=True,exist_ok=True)
 if (out/'receipt.json').exists():
  old=json.loads((out/'receipt.json').read_text())
  assert old['odb_sha256']==sha(R/info['odb']) and old['binary_sha256']==sha(exe)
  assert old['rules_sha256']==sha(old['rules_path']) and old['trace_sha256']==sha(out/'trace.tsv')
  assert old['spef_sha256']==sha(out/'trace.spef')
  continue
 rp=U/'data/raw'/rules[case.split('/')[0]]
 env=dict(os.environ,LD_LIBRARY_PATH=f'{D}/lib64:{D}/lib:'+os.environ.get('LD_LIBRARY_PATH',''),STA_ODB=str(R/info['odb']),DAC_RULES=str(rp),STA_SPEF=str(out/'trace.spef'),DAC_QUERY_TRACE=str(out/'trace.tsv'))
 t=time.perf_counter();before=resource.getrusage(resource.RUSAGE_CHILDREN)
 with (out/'native.log').open('w') as f:subprocess.run([str(exe),'-threads','1','-exit',str(H/'trace.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
 env['STA_SPEF']=str(out/'original.spef');env.pop('DAC_QUERY_TRACE')
 with (out/'original.log').open('w') as f:subprocess.run([str(original),'-threads','1','-exit',str(H/'trace.tcl')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
 after=resource.getrusage(resource.RUSAGE_CHILDREN)
 # SPEF date/header may differ; compare all electrical lines after *D_NET.
 def electrical(p):return '*D_NET'.join(p.read_text().split('*D_NET')[1:])
 same=electrical(out/'trace.spef')==electrical(out/'original.spef');assert same
 rec=dict(case=case,odb_path=env['STA_ODB'],odb_sha256=sha(env['STA_ODB']),rules_path=str(rp),rules_sha256=sha(rp),binary_sha256=sha(exe),original_binary_sha256=sha(original),electrical_spef_identical=same,trace_sha256=sha(out/'trace.tsv'),spef_sha256=sha(out/'trace.spef'),wall_s=time.perf_counter()-t,cpu_s=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
 (out/'receipt.json').write_text(json.dumps(rec,indent=2));print(case,rec['wall_s'],same,flush=True)
