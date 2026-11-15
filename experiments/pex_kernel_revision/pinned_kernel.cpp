// SPDX-License-Identifier: BSD-3-Clause
// Copyright (c) 2019-2025, The OpenROAD Authors
// Exact pinned function bodies; experimental storage/CLI wrapper.
#include <vector>
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
static double lineSegment(double X, double x1, double x2, double y1, double y2)
{
  double slope = (y2 - y1) / (x2 - x1);
  double retVal = y2 - slope * (x2 - X);

  return retVal;
}

void extDistRC::interpolate(uint32_t d, extDistRC* rc1, extDistRC* rc2)
{
  sep_ = d;
  coupling_
      = lineSegment(d, rc1->sep_, rc2->sep_, rc1->coupling_, rc2->coupling_);
  fringe_ = lineSegment(d, rc1->sep_, rc2->sep_, rc1->fringe_, rc2->fringe_);
  res_ = lineSegment(d, rc1->sep_, rc2->sep_, rc1->res_, rc2->res_);
}

uint32_t extDistRCTable::mapExtrapolate(uint32_t loDist,
                                        extDistRC* rc2,
                                        uint32_t distUnit,
                                        AthPool<extDistRC>* rcPool)
{
  uint32_t cnt = 0;
  uint32_t d1 = loDist;
  uint32_t d2 = rc2->sep_;

  for (uint32_t d = d1; d <= d2; d += distUnit) {
    extDistRC* rc = rcPool->alloc();

    rc->sep_ = d;
    rc->coupling_ = rc2->coupling_;
    rc->fringe_ = rc2->fringe_;
    rc->res_ = rc2->res_;

    uint32_t n = d / distUnit;

    computeTable_->set(n, rc);

    cnt++;
  }
  return cnt;
}

uint32_t extDistRCTable::mapInterpolate(extDistRC* rc1,
                                        extDistRC* rc2,
                                        uint32_t distUnit,
                                        int maxDist,
                                        AthPool<extDistRC>* rcPool)
{
  uint32_t cnt = 0;
  uint32_t d1 = rc1->sep_;
  uint32_t d2 = rc2->sep_;

  if ((int) d2 > maxDist) {
    d2 = maxDist;
  }

  for (uint32_t d = d1; d <= d2; d += distUnit) {
    extDistRC* rc = rcPool->alloc();

    rc->sep_ = d;
    rc->interpolate(rc->sep_, rc1, rc2);

    uint32_t n = d / distUnit;

    computeTable_->set(n, rc);

    cnt++;
  }
  return cnt;
}

uint32_t extDistRCTable::interpolate(uint32_t distUnit,
                                     int maxDist,
                                     AthPool<extDistRC>* rcPool)
{
  uint32_t cnt = measureTable_->getCnt();
  uint32_t Cnt = cnt;
  if (cnt == 0) {
    return 0;
  }

  if (maxDist < 0) {
    extDistRC* lastRC = measureTable_->get(cnt - 1);
    maxDist = lastRC->sep_;
    if (maxDist == 100000) {
      maxDist = measureTable_->get(cnt - 2)->sep_;
      if (maxDist == 99000) {
        maxDist = measureTable_->get(cnt - 3)->sep_;
        Cnt = cnt - 2;
      } else {
        Cnt = cnt - 1;
      }
      extDistRC* rc31 = rcPool->alloc();
      rc31->set(0, 0.0, 0.0, 0.0, 0.0);
      measureTable_->set(31, rc31);
    }
  }

  makeComputeTable(maxDist, distUnit);

  mapExtrapolate(0, measureTable_->get(0), distUnit, rcPool);

  for (uint32_t ii = 0; ii < Cnt - 1; ii++) {
    extDistRC* rc1 = measureTable_->get(ii);
    extDistRC* rc2 = measureTable_->get(ii + 1);

    mapInterpolate(rc1, rc2, distUnit, maxDist, rcPool);
  }
  if (Cnt != cnt) {
    extDistRC* rc1 = measureTable_->get(Cnt);
    extDistRC* rc = rcPool->alloc();
    rc->set(rc1->sep_, rc1->coupling_, rc1->fringe_, 0.0, rc1->res_);
    computeTable_->set(computeTable_->getSize() - 1, rc);
  }

  return computeTable_->getCnt();
}

void extDistRCTable::makeComputeTable(uint32_t maxDist, uint32_t distUnit)
{
  unit_ = distUnit;  // in nm
  uint32_t n = maxDist / distUnit;
  n = distUnit * (n / distUnit + 1);

  computeTable_ = new Array1D<extDistRC*>(n + 1);
}

extDistRC* extDistRCTable::getComputeRC(uint32_t dist)
{
  if (measureTable_ == nullptr) {
    return nullptr;
  }

  if (measureTable_->getCnt() <= 0) {
    return nullptr;
  }

  extDistRC* firstRC = measureTable_->get(0);
  uint32_t firstDist = firstRC->sep_;
  if (dist <= firstDist) {
    return firstRC;
  }

  if (measureTable_->getLast()->sep_ == 100000) {
    extDistRC* before_lastRC = measureTable_->getLast()
                               - 1;  // assuming last is 100 equivalent to inf
    uint32_t lastDist = before_lastRC->sep_;

    if (lastDist == 99000) {
      before_lastRC = before_lastRC - 1;
    }

    lastDist = before_lastRC->sep_;
    if (dist >= lastDist) {    // send Inf dist
      if (dist == lastDist) {  // send Inf dist
        return before_lastRC;
      }
      if (dist <= 2 * lastDist) {  // send Inf dist

        uint32_t cnt = measureTable_->getCnt();
        extDistRC* rc31 = measureTable_->geti(31);
        extDistRC* rc2 = measureTable_->get(cnt - 2);
        extDistRC* rc3 = measureTable_->get(cnt - 3);

        rc31->sep_ = dist;
        rc31->interpolate(dist, rc3, rc2);

        rc31->coupling_
            = (before_lastRC->coupling_ / dist) * before_lastRC->sep_;
        rc31->fringe_ = before_lastRC->fringe_;
        return rc31;
      }
      if (dist > lastDist) {  // send Inf dist
        return measureTable_->getLast();
      }
    }
  } else {
    extDistRC* before_lastRC
        = measureTable_->getLast();  // assuming last is 100 equivalent to inf
    uint32_t lastDist = before_lastRC->sep_;
    if (dist >= lastDist - unit_ && lastDist > 0) {  // send Inf dist
      return measureTable_->getLast();
    }
  }

  uint32_t n = dist / unit_;
  return computeTable_->geti(n);
}

void extDistWidthRCTable::createWidthMap()
{
  uint32_t widthCnt = _widthTable->getCnt();
  if (widthCnt == 0) {
    return;
  }

  _firstWidth = _widthTable->get(0);
  _lastWidth = _widthTable->getLast();
  _modulo = 4;

  _widthTableAllocFlag = true;
  _widthMapTable = new Array1D<uint32_t>(10 * widthCnt);

  uint32_t jj;
  for (jj = 0; jj < widthCnt - 1; jj++) {
    double v1 = _widthTable->get(jj);
    double v2 = _widthTable->get(jj + 1);

    int w1 = lround(v1);
    int w2 = lround(v2);

    for (int w = w1; w <= w2; w += _modulo) {
      if (w >= _lastWidth) {
        continue;
      }

      uint32_t n = 0;
      int v = w - _firstWidth;
      if (v > 0) {
        n = v / _modulo;
      }

      _widthMapTable->set(n, jj);
    }
  }
}

uint32_t extDistWidthRCTable::getWidthIndex(uint32_t w)
{
  // To notify that the RC info for a particular pattern
  // is empty
  if (_lastWidth == -1) {
    return -1;
  }

  if ((int) w >= _lastWidth) {
    return _widthTable->getCnt() - 1;
  }

  int v = w - _firstWidth;
  if (v < 0) {
    return 0;
  }

  return _widthMapTable->geti(v / _modulo);
}
int main(){std::cout<<std::setprecision(17);unsigned cases;std::cin>>cases;
while(cases--){unsigned nw,nq,ni;std::cin>>nw>>nq>>ni;AthPool<extDistRC> pool;extDistWidthRCTable width;width._widthTable=new Array1D<unsigned>(nw);std::vector<extDistRCTable> tabs(nw);
for(unsigned j=0;j<nw;j++){unsigned w,n;std::cin>>w>>n;width._widthTable->add(w);tabs[j].measureTable_=new Array1D<extDistRC*>(32);for(unsigned k=0;k<n;k++){unsigned d;double c,f,r;std::cin>>d>>c>>f>>r;auto p=pool.alloc();p->set(d,c,f,0,r);tabs[j].measureTable_->add(p);}tabs[j].interpolate(4,-1,&pool);}width.createWidthMap();
for(unsigned k=0;k<ni;k++){unsigned j,slot;double c,f,r;std::cin>>j>>slot>>c>>f>>r;auto p=tabs.at(j).computeTable_->get(slot);p->coupling_=c;p->fringe_=f;p->res_=r;}
for(unsigned k=0;k<nq;k++){unsigned w,d;std::cin>>w>>d;unsigned j=width.getWidthIndex(w);auto p=tabs[j].getComputeRC(d);std::cout<<j<<" "<<p->sep_<<" "<<p->coupling_<<" "<<p->fringe_<<" "<<p->res_<<"\n";}
for(auto &t:tabs){delete t.measureTable_;delete t.computeTable_;}delete width._widthTable;delete width._widthMapTable;
}}
