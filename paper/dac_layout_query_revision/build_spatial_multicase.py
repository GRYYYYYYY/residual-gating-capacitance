"""Four-process IBEX spatial fidelity, averaged over all three archived seeds.
No STA rerun. Each per-endpoint absolute error is computed before seed averaging.
"""
from pathlib import Path
import csv,gzip,json,re,hashlib,io,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import MaxNLocator
P=Path(__file__).resolve().parent;D=P/'data/downstream_fidelity/multicase'
CASES=[('asap7','ASAP7'),('gf180','GF180'),('ihp-sg13g2','IHP-SG13G2'),('sky130hs','Sky130HS')]
def raw(case,name):return gzip.decompress((case/(name+'.gz')).read_bytes())
def rows(case,name):return list(csv.DictReader(io.StringIO(raw(case,name).decode()),delimiter='\t'))
def canon(s):return s.replace('\\','')
summary=[];seed_summary=[];panels=[]
for platform,title in CASES:
 c=D/platform;manifest=json.loads((c/'source_manifest.json').read_text());verified=json.loads((c/'verification.json').read_text())
 for f in c.glob('*.gz'):
  if f.name=='endpoint_seedmean.csv.gz':continue
  name=f.name[:-3]
  if name in ['layout.tsv','ports.tsv','bounds.tsv']:key='golden/'+name
  else:
   variant,name=name.rsplit('_',1) if name.endswith('_endpoints.tsv') else name.rsplit('_',1)
   key=variant+'/'+name
  assert hashlib.sha256(gzip.decompress(f.read_bytes())).hexdigest()==manifest['source_sha256'][key],key
 layout=rows(c,'layout.tsv');ports=rows(c,'ports.tsv')
 loc={canon(r['instance']):((float(r['xmin'])+float(r['xmax']))/2,(float(r['ymin'])+float(r['ymax']))/2) for r in layout}
 portloc={canon(r['port']):(float(r['x']),float(r['y'])) for r in ports}
 variants=['golden']+[f'{m}_block50_seed{s}' for s in [0,1,2] for m in ['linear','ours']]
 slacks={};finite={};allsets=[];ws={};tns={};units=set()
 for variant in variants:
  log=raw(c,variant+'_sta.log').decode();unit=re.search(r'^\s*time\s+1(ps|ns)\s*$',log,re.M).group(1);units.add(unit)
  r=rows(c,variant+'_endpoints.tsv');s={x['endpoint']:float(x['slack']) for x in r};assert len(s)==len(r)
  ff=np.array([v for v in s.values() if np.isfinite(v)])
  np.testing.assert_allclose(ff.min(),verified['variants'][variant]['worst_slack_native'],atol=1.1e-6,rtol=0)
  np.testing.assert_allclose(np.minimum(ff,0).sum(),verified['variants'][variant]['tns_native'],atol=.02,rtol=0)
  factor=1. if unit=='ps' else 1000.
  slacks[variant]={k:v*factor for k,v in s.items()};finite[variant]={k for k,v in s.items() if np.isfinite(v)};allsets.append(set(s))
  ws[variant]=float(ff.min()*factor);tns[variant]=float(np.minimum(ff,0).sum()*factor)
 assert len(units)==1 and all(x==allsets[0] for x in allsets)
 assert all(x==finite['golden'] for x in finite.values())
 ids=sorted(finite['golden']);coords=[]
 for name in ids:
  k=canon(name);xy=portloc.get(k) if k in portloc else loc.get(k.rsplit('/',1)[0]);assert xy is not None
  coords.append(xy)
 xy=np.array(coords);gold=np.array([slacks['golden'][k] for k in ids]);errors={}
 for m in ['linear','ours']:
  errors[m]=np.array([np.abs(np.array([slacks[f'{m}_block50_seed{s}'][k] for k in ids])-gold) for s in [0,1,2]])
 for s in [0,1,2]:
  ml,mf=errors['linear'][s].mean(),errors['ours'][s].mean()
  seed_summary.append(dict(platform=platform,seed=s,endpoints=len(ids),mae_linear_ps=float(ml),mae_full_ps=float(mf),relative_reduction_pct=float(100*(1-mf/ml)),mean_gain_ps=float(ml-mf)))
 mean_l=errors['linear'].mean(axis=0);mean_f=errors['ours'].mean(axis=0);gain=mean_l-mean_f
 bounds=np.loadtxt(io.BytesIO(raw(c,'bounds.tsv')));edges=[np.linspace(bounds[i],bounds[i+2],51) for i in [0,1]]
 counts=np.histogram2d(xy[:,0],xy[:,1],bins=edges)[0];assert counts.sum()==len(ids)
 sums=np.histogram2d(xy[:,0],xy[:,1],bins=edges,weights=gain)[0]
 grid=np.ma.masked_where(counts.T==0,(sums/np.maximum(counts,1)).T)
 gmax=float(np.max(np.abs(grid)));scale=10**math.floor(math.log10(gmax));limit=math.ceil(gmax/scale)*scale
 rec=dict(platform=platform,design='ibex',mask='block',holdout=.5,seeds=[0,1,2],endpoints=len(ids),unconstrained=len(allsets[0])-len(ids),mae_linear_ps=float(mean_l.mean()),mae_full_ps=float(mean_f.mean()),relative_reduction_pct=float(100*(1-mean_f.mean()/mean_l.mean())),mean_gain_ps=float(gain.mean()),gain_max_abs_ps=gmax,color_limit_ps=limit,geometry_identical=True,endpoint_sets_identical=True,global_sta_verified=True,bins=[50,50])
 summary.append(rec);panels.append((title,bounds,edges,grid,rec))
 with gzip.open(c/'endpoint_seedmean.csv.gz','wt') as f:
  w=csv.writer(f);w.writerow(['endpoint','x_um','y_um','mean_error_linear_ps','mean_error_full_ps','mean_gain_ps'])
  w.writerows((name,*coord,l,o,g) for name,coord,l,o,g in zip(ids,xy,mean_l,mean_f,gain))
# Explicitly verify the original GF180 summaries, including the small seed-2 loss.
expected=list(csv.DictReader((P.parents[1]/'results/sta_visualization/gf180_ibex_50/data/summary_metrics.csv').open()))
for row in seed_summary:
 if row['platform']=='gf180':
  for name,label in [('linear','linear'),('full','ours')]:
   old=next(r for r in expected if int(r['seed'])==row['seed'] and r['method']==label)
   np.testing.assert_allclose(row['mae_'+name+'_ps'],1000*float(old['mae_ns']),rtol=1e-12,atol=1e-10)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':7,'axes.titlesize':7.5,'axes.labelsize':7,'pdf.fonttype':42})
fig,axs=plt.subplots(2,2,figsize=(3.45,3.15),layout='constrained')
axs=axs.ravel()
fig.set_constrained_layout_pads(w_pad=.015,h_pad=.01,wspace=.025,hspace=.04)
for i,(title,b,edges,grid,r) in enumerate(panels):
 ax=axs[i]
 ax.set(xlim=(b[0],b[2]),ylim=(b[1],b[3]),aspect='equal');ax.set_title(title+' / IBEX',pad=4)
 ax.xaxis.set_major_locator(MaxNLocator(3));ax.yaxis.set_major_locator(MaxNLocator(3));ax.tick_params(labelsize=6,pad=1,length=2);ax.set_facecolor('#ededed')
 for spine in ax.spines.values():spine.set_color('#9aa5af')
 lim=r['color_limit_ps'];im=ax.pcolormesh(*edges,grid,cmap='RdBu',norm=TwoSlopeNorm(0,-lim,lim),shading='flat',rasterized=True)
 cb=fig.colorbar(im,ax=ax,fraction=.05,pad=.025);cb.set_ticks([-lim,0,lim]);cb.ax.tick_params(labelsize=6,pad=1,length=2);cb.ax.set_title('ps',fontsize=6.5,pad=3)
 ax.text(.02,.98,f"MAE {r['mae_linear_ps']:.2f} → {r['mae_full_ps']:.2f} ps",transform=ax.transAxes,va='top',fontsize=5.7,bbox=dict(facecolor='white',alpha=.9,edgecolor='none',pad=1))
fig.supxlabel(r'$x$ ($\mu$m)',fontsize=7);fig.supylabel(r'$y$ ($\mu$m)',fontsize=7)
for ext in ['pdf','png']:fig.savefig(P/f'figures/downstream_spatial_multicase.{ext}',dpi=300,bbox_inches='tight',facecolor='white')
plt.close(fig)
(D/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (D/'seed_metrics.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(seed_summary[0]));w.writeheader();w.writerows(seed_summary)
print(json.dumps(summary,indent=2));print('Seed-wise reductions:',[(r['platform'],r['seed'],round(r['relative_reduction_pct'],2)) for r in seed_summary])
