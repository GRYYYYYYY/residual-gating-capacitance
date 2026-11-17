"""Isolated Fig. 4 trial: frozen-model inference, matched aggregation, plot/PDF source.
Run after sourcing experiments/dac_characterization_20261114/env.sh.
No formal paper, original figure, checkpoint or established result is written.
"""
import argparse,collections,csv,gzip,hashlib,json,os,sys,time
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'unified').is_dir())
PAPER=ROOT/'paper/dac_layout_query_revision'
DATA=ROOT/'results/pex_kernel_revision'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def csvwrite(p,rows):
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def key(r):return (r['table_id'],r['protocol'],float(r.get('ratio',r.get('requested_holdout'))),int(r.get('mask_seed',r.get('seed'))))
def check_originals():
 for name,h in json.loads((OUT/'baseline/formal_sha256.json').read_text()).items():assert sha(PAPER/name)==h, name

def evaluate(domain):
 import numpy as np,torch
 sys.path.insert(0,str(ROOT/'experiments/dac_characterization_20261114'))
 import evaluate as old
 import common as cfg
 from pdkcap.sampling import mask
 from pdkcap.metrics import record
 torch.set_num_threads(1)
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
 dest=OUT/f'ungated_{domain}.jsonl.gz'
 receipt=OUT/f'{domain}_receipt.json'
 if receipt.exists():
  assert sha(dest)==json.loads(receipt.read_text())['raw_sha256'];return
 assert not dest.exists(), 'Existing incomplete output: choose a new trial directory.'
 ts=old.tables(domain,'confirmation');start=time.perf_counter();cpu=time.process_time()
 predictor=old.Predictors(domain,learned=False)
 inv={key(r):r for r in csv.DictReader((DATA/f'coverage_inventory_{domain}.csv').open())}
 full=collections.defaultdict(list)
 with gzip.open(DATA/f'coverage_{domain}.jsonl.gz','rt') as f:
  for line in f:
   r=json.loads(line)
   if r['method']=='full':full[key(r)].append(r)
 archive=ROOT/f'experiments/paper_controls/scores/{domain}/learned_confirmation.jsonl.gz'
 observed={}
 with gzip.open(archive,'rt') as f:
  for line in f:
   r=json.loads(line)
   if r['method']=='residual' and r['segment']!='all' and str(r['training_seed'])=='ensemble':observed[key(r)+(r['segment'],)]=r
 reused=inferred=count=0;seen=set()
 with gzip.open(dest,'wt') as f:
  for ti,t in enumerate(ts):
   x=np.asarray(t['coordinates']);y=np.asarray(t['labels']);g=old.public_input(t)
   for proto in ['mcar','block','extrapolation']:
    for ratio in [.1,.3,.5,.7]:
     for seed in [11,29,47,71,101]:
      k=(t['table_id'],proto,ratio,seed);v=inv[k];o,q=mask(x,proto,ratio,seed)
      h=hashlib.sha256(json.dumps([t['table_id'],o.tolist(),q.tolist()],sort_keys=True).encode()).hexdigest()
      assert h==v['SQ_hash'];assert sorted(i for r in full[k] for i in r['scored_indices'])==q.tolist()
      seen.add(k)
      if ratio!=.3:p=predictor('residual',g,o,y[o]);inferred+=1
      else:reused+=1
      for base in full[k]:
       idx=base['scored_indices']
       if ratio==.3:
        r=dict(observed[k+(base['segment'],)])
        assert r['scored_indices']==idx and r['n']==base['n']
        assert np.allclose(r['squared_truth'],base['squared_truth'],rtol=1e-12,atol=0)
        r['origin']='reused frozen three-member 30% accumulator'
       else:
        r=record(t,y[idx],p[idx],method='residual',training_seed='ensemble',protocol=proto,ratio=ratio,mask_seed=seed,segment=base['segment'],scored_indices=idx,origin='new frozen three-member inference; no training')
        assert np.allclose(r['squared_truth'],base['squared_truth'],rtol=1e-12,atol=0)
       r.update(domain_setting=domain,SQ_hash=h,support_indices=o.tolist(),openrcx_applicable=v['openrcx_applicable']=='True')
       f.write(json.dumps(r,allow_nan=False)+'\n');count+=1
   if (ti+1)%25==0 or ti+1==len(ts):print(domain,ti+1,'/',len(ts),'tables',round(time.perf_counter()-start,1),'s',flush=True)
 assert seen==set(inv)
 checkpoints=[]
 for seed in range(3):
  d=Path(cfg.PATHS['control_root'])/'runs'/f'{domain}_residual_s{seed}'
  checkpoints.append({'path':str(d/'checkpoint.pt'),'sha256':sha(d/'checkpoint.pt'),'frozen_sha256':sha(d/'FROZEN.json')})
 dump(receipt,dict(domain=domain,tables=len(ts),episodes=len(seen),reused_30pct_episodes=reused,new_inference_episodes=inferred,records=count,raw_sha256=sha(dest),archive_sha256=sha(archive),inventory_sha256=sha(DATA/f'coverage_inventory_{domain}.csv'),reference_records_sha256=sha(DATA/f'coverage_{domain}.jsonl.gz'),checkpoints=checkpoints,ensemble_members=3,trained=False,cpu_s=time.process_time()-cpu,wall_s=time.perf_counter()-start,alignment='Exact inventory support/query hash, segment indices and squared-truth checks for every episode.'))
 check_originals()

def aggregate(records,method):
 import numpy as np
 acc={}
 for r in records:
  reg='outside' if r['segment']=='outside' else 'inside'
  k=(r['ratio'],reg,r['protocol'],r['mask_seed'],r['process_id'],r['family'])
  e=np.asarray(r['squared_error']);y=np.asarray(r['squared_truth'])
  if k not in acc:acc[k]=[e.copy(),y.copy()]
  else:acc[k][0]+=e;acc[k][1]+=y
 masks=collections.defaultdict(list)
 for k,(e,y) in acc.items():masks[k[:4]].extend(np.sqrt(e[y>0]/y[y>0]).tolist())
 groups=collections.defaultdict(list)
 for k,vals in masks.items():
  if vals:groups[k[:3]].append(float(np.mean(vals)))
 return [dict(method=method,requested_holdout=k[0],regime=k[1],protocol=k[2],macro_nrmse=float(np.mean(v)),mask_count=len(v)) for k,v in groups.items()]

def plot():
 import numpy as np,matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 scores=list(csv.DictReader((OUT/'baseline/support_coverage_scores.csv').open()));selected=[];checks={}
 for domain in ['public','reference','to_asap7']:
  inv={r['SQ_hash'] for r in csv.DictReader((DATA/f'coverage_inventory_{domain}.csv').open()) if r['openrcx_applicable']=='True'}
  # Reproduce Full from the raw accumulators to verify the exact existing statistic.
  with gzip.open(DATA/f'coverage_{domain}.jsonl.gz','rt') as f:
   full=aggregate((r for r in map(json.loads,f) if r['method']=='full' and r['SQ_hash'] in inv),'full')
  differences=[]
  for r in full:
   b=next(s for s in scores if s['domain']==domain and s['method']=='full' and s['population']=='common' and float(s['requested_holdout'])==r['requested_holdout'] and s['regime']==r['regime'] and s['protocol']==r['protocol'])
   differences.append(abs(float(b['macro_nrmse'])-r['macro_nrmse']))
   assert differences[-1]<1e-14 and int(b['mask_count'])==r['mask_count']
  checks[domain]=dict(full_reaggregation_max_abs_error=max(differences),matched_cells=len(full))
  with gzip.open(OUT/f'ungated_{domain}.jsonl.gz','rt') as f:
   ungated=aggregate((r for r in map(json.loads,f) if r['SQ_hash'] in inv),'residual')
  for r in ungated:selected.append(dict(domain=domain,population='common',**r))
 for s in scores:
  if s['population']=='common' and s['method'] in ['mli_sparse','openrcx_kernel','binary','full'] and s['regime'] in ['inside','outside']:
   selected.append(dict(domain=s['domain'],population='common',method=s['method'],requested_holdout=float(s['requested_holdout']),regime=s['regime'],protocol=s['protocol'],macro_nrmse=float(s['macro_nrmse']),mask_count=int(s['mask_count'])))
 cond=[('inside','mcar','In/random'),('inside','block','In/block'),('outside','mcar','Out/random'),('outside','block','Out/block'),('outside','extrapolation','Boundary')]
 methods=['mli_sparse','openrcx_kernel','binary','full','residual']
 labels=['MLI + sparse extension','OpenRCX kernel','Binary','Full','Ungated']
 colors=['#777777','#46816d','#176394','#b34332','#9467bd'];markers=['v','^','o','s','D']
 plt.rcParams.update({'font.size':8,'font.family':'DejaVu Sans','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
 fig,axs=plt.subplots(3,5,figsize=(7.1,4.5),sharex=True);fig.subplots_adjust(left=.085,right=.99,bottom=.11,top=.88,wspace=.36,hspace=.42)
 for i,(domain,title) in enumerate([('public','Public'),('reference','FEM'),('to_asap7','Transfer')]):
  for j,(reg,proto,cl) in enumerate(cond):
   for method,label,color,marker in zip(methods,labels,colors,markers):
    rr=sorted([s for s in selected if s['domain']==domain and s['method']==method and s['regime']==reg and s['protocol']==proto],key=lambda r:r['requested_holdout'])
    assert [r['requested_holdout'] for r in rr]==[.1,.3,.5,.7],(domain,method,reg,proto)
    axs[i,j].plot([100*r['requested_holdout'] for r in rr],[r['macro_nrmse'] for r in rr],linestyle='--' if method=='openrcx_kernel' else '-.' if method=='residual' else '-',marker=marker,color=color,label=label,lw=1,ms=3)
   axs[i,j].set_yscale('log');axs[i,j].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter());axs[i,j].tick_params(labelsize=8);axs[i,j].set_xticks([10,30,50,70]);axs[i,j].grid(alpha=.15)
   if i==0:axs[i,j].set_title(cl,fontsize=8)
   if j==0:axs[i,j].set_ylabel(title+' NRMSE',fontsize=8)
 fig.legend(*axs[0,0].get_legend_handles_labels(),loc='upper center',ncol=5,frameon=False,fontsize=7.5,columnspacing=1.1,handletextpad=.4)
 fig.text(.5,.015,'Requested characterization holdout (%)',ha='center')
 for ext in ['pdf','png']:fig.savefig(OUT/('coverage_four_ratios_ungated.'+ext),bbox_inches='tight',dpi=180)
 plt.close(fig);csvwrite(OUT/'plotted_scores.csv',selected);dump(OUT/'aggregation_checks.json',checks)
 s=(OUT/'baseline/main.tex').read_text();relative=OUT.relative_to(PAPER).as_posix()
 s=s.replace('figures/coverage_four_ratios.pdf',relative+'/coverage_four_ratios_ungated.pdf')
 assert 'Full and Binary average three matched members.' in s
 s=s.replace('Full and Binary average three matched members.','Full, Binary, and Ungated average three matched members.',1)
 (OUT/'main_ungated.tex').write_text(s)
 (OUT/'main_ungated.bbl').write_bytes((OUT/'baseline/main.bbl').read_bytes())
 check_originals();print('Plot and trial source ready:',OUT,flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--domain',choices=['public','reference','to_asap7']);ap.add_argument('--plot',action='store_true');args=ap.parse_args()
 if args.domain:evaluate(args.domain)
 if args.plot:plot()
