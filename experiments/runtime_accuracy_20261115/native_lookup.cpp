// Finite rank-one OpenRCX compute-table semantics, source-validated counterpart.
// Scope: a resolved width/context table; excludes upstream geometry discovery.
#include <vector>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <chrono>
#include <ctime>
using V=std::array<double,2>;
struct Table {std::vector<int> x;std::vector<V> v,grid;};
static std::vector<Table> tables;
static std::vector<std::pair<int,int>> queries;
static volatile double checksum=0;
using Clock=std::chrono::steady_clock;
static double seconds(Clock::time_point a){return std::chrono::duration<double>(Clock::now()-a).count();}
extern "C" int load_tables(const char* path){
 std::ifstream in(path);int n;in>>n;tables.clear();queries.clear();
 for(int j=0;j<n;j++){
  int m;in>>m;Table t;t.x.resize(m);t.v.resize(m);
  for(int i=0;i<m;i++)in>>t.x[i]>>t.v[i][0]>>t.v[i][1];
  if(m<2 || t.x.back()==100000)return -1;
  t.grid.resize(t.x.back()/4+1,V{NAN,NAN});
  for(int i=0;i<m-1;i++)for(int d=t.x[i];d<=t.x[i+1];d+=4){
   double alpha=double(d-t.x[i])/double(t.x[i+1]-t.x[i]);
   for(int k=0;k<2;k++)t.grid[d/4][k]=t.v[i][k]+alpha*(t.v[i+1][k]-t.v[i][k]);
  }tables.push_back(std::move(t));
 }
 in>>n;for(int i=0;i<n;i++){int ti,d;in>>ti>>d;queries.emplace_back(ti,d);}return in?int(queries.size()):-2;
}
static inline V get(int ti,int d){
 const auto &t=tables[ti];
 if(d<=t.x.front())return t.v.front();
 if(d>=t.x.back()-4 && t.x.back()>0)return t.v.back();
 return t.grid[d/4];
}
extern "C" void lookup(int i,double* out){auto q=queries[i];auto v=get(q.first,q.second);out[0]=v[0];out[1]=v[1];}
static double run(std::uint64_t reps){
 double sum=0;
 for(std::uint64_t rep=0;rep<reps;rep++)for(auto q:queries){auto v=get(q.first,q.second);sum+=v[0]+v[1];}
 checksum=sum;return sum;
}
int main(int argc,char**argv){
 auto s=Clock::now();double c=double(std::clock())/CLOCKS_PER_SEC;int n=load_tables(argv[1]);
 std::cout<<std::setprecision(17)<<"setup,"<<seconds(s)<<","<<double(std::clock())/CLOCKS_PER_SEC-c<<","<<n<<"\n";
 if(n<=0)return 2;
 for(int i=0;i<n;i++){double v[2];lookup(i,v);std::cout<<"prediction,"<<i<<","<<v[0]<<","<<v[1]<<"\n";}
 // Pilot fixes a loop long enough to avoid timer/subprocess granularity.
 s=Clock::now();run(1000);double pilot=seconds(s);std::uint64_t reps=std::max<std::uint64_t>(1000,std::ceil(.03/std::max(pilot,1e-9)*1000));
 std::cout<<"pilot,"<<pilot<<","<<reps<<","<<n<<"\n";
 for(int i=-3;i<20;i++){
  s=Clock::now();c=double(std::clock())/CLOCKS_PER_SEC;double sum=run(reps);double wall=seconds(s),cpu=double(std::clock())/CLOCKS_PER_SEC-c;
  if(i>=0)std::cout<<"timing,"<<i<<","<<wall<<","<<cpu<<","<<reps<<","<<n<<","<<sum<<"\n";
 }
 return std::isfinite(checksum)?0:3;
}
