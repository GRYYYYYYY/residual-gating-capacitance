"""Patch one translation unit and relink isolated archives; originals read only."""
from common import *
import subprocess,shlex,shutil,difflib
out=O/'build';out.mkdir(exist_ok=True)
s=(SRC/'src/rcx/src/extRCmodel.cpp').read_text();original=s
s=s.replace('namespace rcx {','#include <iomanip>\nnamespace rcx {\n'+(H/'compute_hook.hpp').read_text(),1)
# Explicit corner and per-read context; unsupported diagonal/resistance clear it.
a='  uint32_t cnt = 0;\n  uint32_t met = 0;\n  Array1D<double>* wTable'
s=s.replace(a,'  dac_ct.corner=m; dac_ct.context.clear();\n'+a,1)
for method,end,family,below,above in [('readRulesOver','readRulesUnder','OVER','ii','0'),('readRulesUnder','readRulesDiagUnder','UNDER','0','ii'),('readRulesOverUnder','getMetIndexUnder','OVERUNDER','mUnder','mOver')]:
 start=s.index('uint32_t extDistWidthRCTable::'+method+'(');stop=s.index('uint32_t extDistWidthRCTable::'+end+'(',start+1)
 part=s[start:stop];needle='for (uint32_t jj = 0; jj < widthCnt; jj++) {'
 assert part.count(needle)==1
 cond='!ignore && !res' if family=='OVER' else '!ignore'
 part=part.replace(needle,needle+f'\n      if ({cond}) dac_context("{family}",_met,{below},{above},_widthTable->get(jj)); else dac_ct.context.clear();')
 s=s[:start]+part+s[stop:]
needle='  if (compute) {\n    interpolate(4, -1, rcPool);\n  }'
assert s.count(needle)==1
s=s.replace(needle,'  if (compute) {\n    auto dac_start=dac_now();\n    interpolate(4, -1, rcPool);\n    dac_ct.build_s+=dac_seconds(dac_start);\n    if (!dac_ct.context.empty()) dac_populate(this,measureTable_,computeTable_,unit_);\n  }')
# Clear unsupported diagonal context in both overloads.
needle='  uint32_t cnt = 0;\n  for (uint32_t ii = _met + 1; ii <'
s=s.replace(needle,'  dac_ct.context.clear();\n'+needle) # UNDER resets then sets each supported width.
needle='  return _rcDistTable[mou][wIndex]->getRC(s, true);';assert s.count(needle)==1
s=s.replace(needle,'''#ifdef DAC_CT_TRACE
  auto* tab=_rcDistTable[mou][wIndex]; auto* r=tab->getRC(s,true);
  if(dac_ct.trace && r)dac_ct.trace<<dac_ct.keys[tab]<<"\\t"<<w<<"\\t"<<s<<"\\t"<<r->sep_<<"\\t"<<std::setprecision(17)<<r->coupling_<<"\\t"<<r->fringe_<<"\\t"<<r->res_<<"\\n";
  return r;
#else
'''+needle+'\n#endif')
(out/'extRCmodel.cpp').write_text(s)
(H/'openroad_compute_table.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/src/rcx/src/extRCmodel.cpp',tofile='b/src/rcx/src/extRCmodel.cpp')))
flags={}
for line in (BUILD/'src/rcx/src/CMakeFiles/rcx_lib.dir/flags.make').read_text().splitlines():
 if line.startswith('CXX_'):k,v=line.split(' = ',1);flags[k]=shlex.split(v)
start=stamp();commands=[]
for variant in ['release','trace']:
 archive=out/f'librcx_{variant}.a';shutil.copy2(BUILD/'src/rcx/src/librcx_lib.a',archive)
 cmd=['/usr/bin/g++','-I'+str(SRC/'src/rcx/src'),*flags['CXX_DEFINES'],*flags['CXX_INCLUDES'],*flags['CXX_FLAGS'],*(['-DDAC_CT_TRACE'] if variant=='trace' else []),'-c',str(out/'extRCmodel.cpp'),'-o',str(out/'extRCmodel.cpp.o')]
 link=shlex.split((BUILD/'src/CMakeFiles/openroad.dir/link.txt').read_text());link=[str(archive) if x.endswith('rcx/src/librcx_lib.a') else ('-flto=3' if x=='-flto=auto' else x) for x in link];link[link.index('-o')+1]=str(out/f'openroad-{variant}')
 cs=[cmd,['/usr/bin/gcc-ar-11','r',str(archive),str(out/'extRCmodel.cpp.o')],link]
 with (out/f'{variant}.log').open('w') as f:
  for c in cs:print(variant,c[0],flush=True);subprocess.run(c,cwd=BUILD/'src',stdout=f,stderr=subprocess.STDOUT,check=True);commands.append(c)
 u=resource.getrusage(resource.RUSAGE_CHILDREN)
 write(out/'receipt.json',dict(commands=commands,wall_s=elapsed(start)['wall_s'],cpu_s=u.ru_utime+u.ru_stime,source_commit=subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip(),source_sha256=sha(out/'extRCmodel.cpp'),completed_variant=variant))
