from common import *
import collections
rs=list(csv.DictReader((R/'results/layout_offgrid_20261115/query_census.csv').open()));groups=collections.defaultdict(list)
for r in rs:groups[r['process']+'/'+r['design']].append(r)
out=[]
for case,rr in sorted(groups.items()):
 c=collections.Counter()
 for r in rr:c[r['query_class']]+=int(r['occurrences'])
 total=sum(c.values());finite=total-c['fringe_or_unsupported'];off=c['off_grid_in_support']+c['off_grid_out_of_support'];qn=sum(int(r['quantized_to_node']) for r in rr)
 out.append(dict(case=case,total_calls=total,finite_calls=finite,on_grid_calls=c['on_grid'],inside_offgrid=c['off_grid_in_support'],outside_offgrid=c['off_grid_out_of_support'],special=c['fringe_or_unsupported'],raw_offgrid_calls=off,quantized_to_node=qn,effective_nonnode_from_raw_offgrid=off-qn,raw_fraction_all=off/total,raw_fraction_finite=off/finite,effective_fraction_all=(off-qn)/total,effective_fraction_finite=(off-qn)/finite))
assert sum(r['total_calls'] for r in out)==9888586
csvwrite(O/'query_census_by_layout.csv',out)
write(O/'census_provenance.json',dict(input_sha256=sha(R/'results/layout_offgrid_20261115/query_census.csv'),call_scope='two logged getters, occurrence weighted; not all PEX operations or runtime fractions',all_layout_raw_above_30percent=all(r['raw_fraction_all']>.3 for r in out)))
# Replot the same recorded demand with legends outside the data area.
import gzip
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
old=R/'results/layout_offgrid_20261115';raw=old/'query_manifest.jsonl';compact=O/'census_plot_queries.jsonl.gz'
if raw.exists():
 chosen=[]
 with raw.open() as f:
  for line in f:
   r=json.loads(line)
   if r['process']=='asap7' and r['call_type']=='Q' and r['layer']==4 and r['query_class'] in ['on_grid','off_grid_in_support','off_grid_out_of_support'] and 0<r['raw_coordinates'][1]<1:
    chosen.append({k:r[k] for k in ['query_class','raw_coordinates','occurrence_count']})
 with compact.open('wb') as f:
  with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as g:g.write(('\n'.join(json.dumps(r,sort_keys=True) for r in chosen)+'\n').encode())
 write(O/'census_plot_source.json',dict(manifest_sha256=sha(raw),selection='ASAP7 call_typeQ layer4,0<spacing<1um, finite query classes; no changes to geometries or occurrences'))
else:
 chosen=[json.loads(l) for l in gzip.open(compact,'rt')]
supp=read(old/'native_supports.json');kn=np.unique(np.array([x[:2] for t in supp.values() if t['process_id']=='asap7' and t['metal']==4 for x in t['coordinates']]),axis=0)
csvwrite(O/'census_plot_knots.csv',[dict(width_um=float(w),spacing_um=float(d)) for w,d in kn])
plt.rcParams.update({'font.size':8,'pdf.fonttype':42})
fig,axes=plt.subplots(1,2,figsize=(7.1,2.9));fig.subplots_adjust(left=.075,right=.99,bottom=.26,top=.76,wspace=.38)
classes=[('on_grid','Node','#287bb5','on_grid_calls'),('off_grid_in_support','Non-node inside','#dd8c26','inside_offgrid'),('off_grid_out_of_support','Non-node outside','#a04e81','outside_offgrid'),('fringe_or_unsupported','Fringe/special','#8c8c8c','special')]
bottom=np.zeros(len(out))
for cl,label,col,key in classes:
 vals=np.array([r[key]/r['total_calls']*100 for r in out]);axes[0].bar(range(len(out)),vals,bottom=bottom,label=label,color=col,width=.72);bottom+=vals
axes[0].set_xticks(range(len(out)),[r['case'].replace('ihp-sg13g2','IHP').replace('sky130hs','Sky') for r in out],rotation=50,ha='right');axes[0].set_ylabel('Logged calls (%)');axes[0].set_ylim(0,103)
for cl,label,col,key in classes[:3]:
 rr=[r for r in chosen if r['query_class']==cl];axes[1].scatter([r['raw_coordinates'][1] for r in rr],[r['raw_coordinates'][0] for r in rr],s=[2+np.log1p(r['occurrence_count']) for r in rr],alpha=.5,c=col)
axes[1].scatter(kn[:,1],kn[:,0],marker='x',s=12,c='black',linewidths=.6)
axes[1].set_xlabel(r'Requested spacing ($\mu$m), ASAP7 M4');axes[1].set_ylabel(r'Requested width ($\mu$m)');axes[1].set_yticks([.018,.024,.032])
h,l=axes[0].get_legend_handles_labels();h.append(Line2D([],[],marker='x',color='black',linestyle='None'));l.append('Original knots')
fig.legend(h,l,ncol=3,loc='upper center',frameon=False,fontsize=8,columnspacing=1.4)
for ext in ['pdf','png']:fig.savefig(R/f'paper/dac_layout_query_revision/figures/query_census.{ext}',dpi=200,bbox_inches='tight')
plt.close(fig)
