"""Extract exact pinned function bodies; minimal storage wrapper, not full PEX."""
from common import *
import subprocess
src=(SRC/'src/rcx/src/extRCmodel.cpp').read_text();names=['static double lineSegment(','void extDistRC::interpolate(','uint32_t extDistRCTable::mapExtrapolate(','uint32_t extDistRCTable::mapInterpolate(','uint32_t extDistRCTable::interpolate(','void extDistRCTable::makeComputeTable(','extDistRC* extDistRCTable::getComputeRC(','void extDistWidthRCTable::createWidthMap(','uint32_t extDistWidthRCTable::getWidthIndex('];parts=[]
for name in names:
 a=src.index(name);b=src.index('{',a);depth=1;i=b+1
 while depth:
  if src[i]=='{':depth+=1
  elif src[i]=='}':depth-=1
  i+=1
 parts.append(src[a:i])
pre=r'''#include <vector>
#include <cstdint>
#include <cmath>
#include <algorithm>
#include <iostream>
#include <iomanip>
#include "pinned_array1.h"
using rcx::Array1D;
template<class T>struct AthPool{std::vector<T*> ptr;T* alloc(){auto p=new T{};ptr.push_back(p);return p;}~AthPool(){for(auto p:ptr)delete p;}};
struct extDistRC{int sep_=0;double coupling_=0,fringe_=0,res_=0;void set(unsigned d,double c,double f,double,double r){sep_=d;coupling_=c;fringe_=f;res_=r;}void interpolate(uint32_t,extDistRC*,extDistRC*);};
struct extDistRCTable{Array1D<extDistRC*>* measureTable_=nullptr;Array1D<extDistRC*>* computeTable_=nullptr;unsigned unit_=4;uint32_t mapExtrapolate(uint32_t,extDistRC*,uint32_t,AthPool<extDistRC>*);uint32_t mapInterpolate(extDistRC*,extDistRC*,uint32_t,int,AthPool<extDistRC>*);uint32_t interpolate(uint32_t,int,AthPool<extDistRC>*);void makeComputeTable(uint32_t,uint32_t);extDistRC* getComputeRC(uint32_t);};
struct extDistWidthRCTable{Array1D<unsigned>* _widthTable;Array1D<unsigned>* _widthMapTable;int _firstWidth=0,_lastWidth=0;unsigned _modulo=4;bool _widthTableAllocFlag=false;void createWidthMap();uint32_t getWidthIndex(uint32_t);};
'''
main=r'''
int main(){std::cout<<std::setprecision(17);unsigned cases;std::cin>>cases;
while(cases--){unsigned nw,nq,ni;std::cin>>nw>>nq>>ni;AthPool<extDistRC> pool;extDistWidthRCTable width;width._widthTable=new Array1D<unsigned>(nw);std::vector<extDistRCTable> tabs(nw);
for(unsigned j=0;j<nw;j++){unsigned w,n;std::cin>>w>>n;width._widthTable->add(w);tabs[j].measureTable_=new Array1D<extDistRC*>(32);for(unsigned k=0;k<n;k++){unsigned d;double c,f,r;std::cin>>d>>c>>f>>r;auto p=pool.alloc();p->set(d,c,f,0,r);tabs[j].measureTable_->add(p);}tabs[j].interpolate(4,-1,&pool);}width.createWidthMap();
for(unsigned k=0;k<ni;k++){unsigned j,slot;double c,f,r;std::cin>>j>>slot>>c>>f>>r;auto p=tabs.at(j).computeTable_->get(slot);p->coupling_=c;p->fringe_=f;p->res_=r;}
for(unsigned k=0;k<nq;k++){unsigned w,d;std::cin>>w>>d;unsigned j=width.getWidthIndex(w);auto p=tabs[j].getComputeRC(d);std::cout<<j<<" "<<p->sep_<<" "<<p->coupling_<<" "<<p->fringe_<<" "<<p->res_<<"\n";}
for(auto &t:tabs){delete t.measureTable_;delete t.computeTable_;}delete width._widthTable;delete width._widthMapTable;
}}
'''
(H/'pinned_kernel.cpp').write_text('// SPDX-License-Identifier: BSD-3-Clause\n// Copyright (c) 2019-2025, The OpenROAD Authors\n// Exact pinned function bodies; experimental storage/CLI wrapper.\n'+pre+'\n\n'.join(parts)+main)
(H/'pinned_array1.h').write_bytes((SRC/'src/rcx/include/rcx/array1.h').read_bytes())
subprocess.run(['g++','-O3','-DNDEBUG','-std=c++17',str(H/'pinned_kernel.cpp'),'-o',str(O/'pinned_kernel')],check=True)
write(O/'extracted_kernel.json',dict(source_commit='0b54bb3203e0895f87940ff982358a6e4d406e28',original_source_sha256=sha(SRC/'src/rcx/src/extRCmodel.cpp'),extracted_functions={n:hashlib.sha256(p.encode()).hexdigest() for n,p in zip(names,parts)},harness_sha256=sha(H/'pinned_kernel.cpp'),scope='unmodified function bodies, pinned Array1D and minimal pool storage, finite no-sentinel only; projected component scalars, not full extraction',license='OpenROAD BSD-3-Clause; source attribution retained'))
