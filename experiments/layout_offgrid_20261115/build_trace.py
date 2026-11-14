"""Read-only instrumentation in an isolated archive; original build untouched."""
import os,re,shlex,subprocess,json,hashlib,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=Path('/inspire/hdd/global_user/guoruiyuan-253208540291/ICLR2026/tools/OpenROAD-flow-scripts/tools/OpenROAD')
BUILD=SRC/'build-cpu-20260909'
OUT=ROOT/'results/layout_offgrid_20261115/build';OUT.mkdir(exist_ok=True)
src=(SRC/'src/rcx/src/extRCmodel.cpp').read_text()
helper=r'''
// DAC read-only, single-thread trace. Never changes a returned value.
static FILE* dac_trace() {
 static FILE* f = [](){const char* p=std::getenv("DAC_QUERY_TRACE");return p?std::fopen(p,"w"):nullptr;}(); return f;
}
'''
src=src.replace('namespace rcx {','namespace rcx {\n'+helper,1)
needle='  uint32_t cnt = measureTable_->getCnt();\n  uint32_t Cnt = cnt;'
assert src.count(needle)==1
src=src.replace(needle,needle+r'''
  if (FILE* f=dac_trace()) {
    for(uint32_t i=0;i<cnt;i++) {auto r=measureTable_->get(i);
      std::fprintf(f,"K\t%p\t%u\t%u\t%.17g\t%.17g\n",(void*)this,i,r->sep_,r->coupling_,r->fringe_);
    }
  }
''')
needle='  return _rcDistTable[mou][wIndex]->getRC(s, true);'
assert src.count(needle)==1
src=src.replace(needle,r'''
  auto* table=_rcDistTable[mou][wIndex];
  auto* result=table->getRC(s,true);
  if(FILE* f=dac_trace()) {
    std::fprintf(f,"Q\t%p\t%u\t%d\t%u\t%u\t%d\t%u\t%d\t%.17g\t%.17g\n",
      (void*)table,_met,(int)_over,mou,w,_widthTable->get(wIndex),s,
      result?(int)result->sep_:-1,result?result->coupling_:0.,result?result->fringe_:0.);
  }
  return result;''')
# Fringe lookups are separate from finite-distance queries; retain denominator.
needle='  return rc;\n}\n\nextDistRC* extDistWidthRCTable::getLastWidthFringeRC'
assert src.count(needle)==1
src=src.replace(needle,r'''
  if(FILE* f=dac_trace()) std::fprintf(f,"F\t%p\t%u\t%d\t%u\t%u\t%d\t%d\t%d\t%.17g\t%.17g\n",
    (void*)_rcDistTable[mou][wIndex],_met,(int)_over,mou,w,_widthTable->get(wIndex),index_dist,
    rc?(int)rc->sep_:-1,rc?rc->coupling_:0.,rc?rc->fringe_:0.);
  return rc;
}

extDistRC* extDistWidthRCTable::getLastWidthFringeRC''')
(OUT/'extRCmodel.cpp').write_text(src)
flags={}
for line in (BUILD/'src/rcx/src/CMakeFiles/rcx_lib.dir/flags.make').read_text().splitlines():
 if line.startswith('CXX_'):
  k,v=line.split(' = ',1);flags[k]=shlex.split(v)
commands=[['/usr/bin/g++','-I'+str(SRC/'src/rcx/src'),*flags['CXX_DEFINES'],*flags['CXX_INCLUDES'],*flags['CXX_FLAGS'],'-c',str(OUT/'extRCmodel.cpp'),'-o',str(OUT/'extRCmodel.cpp.o')]]
import shutil
shutil.copy2(BUILD/'src/rcx/src/librcx_lib.a',OUT/'librcx_lib.a')
commands += [['/usr/bin/gcc-ar-11','r',str(OUT/'librcx_lib.a'),str(OUT/'extRCmodel.cpp.o')]]
link=shlex.split((BUILD/'src/CMakeFiles/openroad.dir/link.txt').read_text())
link=[str(OUT/'librcx_lib.a') if x.endswith('rcx/src/librcx_lib.a') else ('-flto=4' if x=='-flto=auto' else x) for x in link]
link[link.index('-o')+1]=str(OUT/'openroad-trace')
commands.append(link)
start=time.perf_counter()
with (OUT/'build.log').open('w') as f:
 for c in commands:
  print('running',c[0],flush=True);subprocess.run(c,cwd=BUILD/'src',stdout=f,stderr=subprocess.STDOUT,check=True)
u=resource.getrusage(resource.RUSAGE_CHILDREN)
(OUT/'receipt.json').write_text(json.dumps(dict(commands=commands,wall_s=time.perf_counter()-start,cpu_s=u.ru_utime+u.ru_stime,source_commit=subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip(),source_hash=hashlib.sha256(src.encode()).hexdigest()),indent=2))
