"""Traceable reuse of counts, strong baselines, coverage and cost; no new inference."""
from pathlib import Path
import json,csv,hashlib,collections,subprocess,sys
import numpy as np
R=Path(__file__).resolve().parents[2];O=R/'results/dac_main13_integrated_revision/main13_20261117';D=R/'docs/dac_main13_integrated_revision';P=R/'paper/dac_layout_query_revision'
def read(p):return json.loads((R/p).read_text())
def rows(p):return list(csv.DictReader((R/p).open()))
def write(name,rs):
 with (O/name).open('w') as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)));w.writeheader();w.writerows(rs)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
def main():
 mapping=[]
 for filename in ['public_inventory_v1/tables.jsonl','public_inventory_holdout_v1/tables.jsonl','round3_evaluation_inputs_v1/public_retrospective_original.jsonl']:
  ts=[json.loads(l) for l in (R/'runs'/filename).read_text().splitlines()]
  for part in sorted({t['partition'] for t in ts}):
   pool=[t for t in ts if t['partition']==part];seen=set();unique=[]
   for t in pool:
    k=tuple(t['curve_hashes'])
    if k not in seen:seen.add(k);unique.append(t)
   mapping.append(dict(file='runs/'+filename,partition=part,raw_tables=len(pool),unique_curve_tables=len(unique),at_least_four=sum(len(t['coordinates'])>=4 for t in unique),at_least_eight=sum(len(t['coordinates'])>=8 for t in unique)))
 write('data_count_mapping.csv',mapping)
 # Recompute the displayed raw five-method curves and expose strong controls.
 budget=rows('paper/dac_layout_query_revision/tables/fixed_budget_all.csv')
 write('fixed_budget_controls.csv',budget)
 labels={'full':'Full','binary':'Binary','residual':'Ungated','mlp_adapt':'MLP (adapted)','gp':'Selected GP','cnp':'CNP','attentioncap_adapted':'Adapted AC','anchor':'Anchor','affine':'Affine','pchip':'PCHIP','cmi':'MLI-ext.'}
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 plt.rcParams.update({'font.size':8,'pdf.fonttype':42})
 fig,axs=plt.subplots(1,3,figsize=(7.1,2.7));methods=['full','binary','residual','mlp_adapt','gp','cnp','attentioncap_adapted']
 for ax,domain,title in zip(axs,['public','reference','to_asap7'],['Public','FEM','Transfer']):
  for m in methods:
   rs=sorted([r for r in budget if r['setting']==domain and r['method']==m],key=lambda r:int(r['budget']))
   if rs:ax.plot([int(r['budget']) for r in rs],[float(r['macro_nrmse']) for r in rs],marker='o',ms=2,lw=1,label=labels[m])
  ax.set(yscale='log',xscale='log',title=title,xlabel='Observed samples B');ax.grid(alpha=.2)
  bs=sorted({int(r['budget']) for r in budget if r['setting']==domain});ax.set_xticks(bs,[str(b) for b in bs]);ax.xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
 axs[0].set_ylabel('Macro NRMSE');handles,legend=axs[1].get_legend_handles_labels();fig.legend(handles,legend,loc='upper center',ncol=4,fontsize=7);fig.tight_layout(rect=(0,0,1,.84))
 for ext in ['pdf','png']:fig.savefig(P/f'figures/fixed_budget_strong_controls.{ext}',dpi=180,bbox_inches='tight')
 tex=[r'\begin{tabular}{llrrrrrrrr}',r'\toprule',r'Domain & $B$ & Anchor & GP & PCHIP & Affine & MLP & Ungated & Binary & Full \\',r'\midrule']
 for domain,title in [('public','Public'),('reference','FEM'),('to_asap7','Transfer')]:
  for b in ([4,8] if domain=='public' else [4,8,16,32,64]):
   vals=[]
   for m in ['anchor','gp','pchip','affine','mlp_adapt','residual','binary','full']:
    a=[r for r in budget if r['setting']==domain and r['method']==m and int(r['budget'])==b];vals.append(f"{float(a[0]['macro_nrmse']):.4f}" if a else '--')
   tex.append(' & '.join([title,str(b),*vals])+r' \\')
 tex +=[r'\bottomrule',r'\end{tabular}'];(P/'tables/strong_numerical.tex').write_text('\n'.join(tex)+'\n')
 census=rows('results/pex_kernel_revision/query_census_by_layout.csv');checks=read('results/pex_kernel_revision/pass_through.json')['checks'];coverage=[]
 for r in census:
  check=next(c for c in checks if c['case']==r['case'] and c['method']=='full');assert int(r['finite_calls'])==check['getter_calls']
  coverage.append(dict(case=r['case'],protocol='full_characterization_compute_table',all_two_getter_calls=int(r['total_calls']),raw_nonnode=int(r['raw_offgrid_calls']),quantized_raw_to_node=int(r['quantized_to_node']),effective_nonnode_from_raw=int(r['effective_nonnode_from_raw_offgrid']),finite_getter_calls=check['getter_calls'],populated_returns=check['injected_getter_calls'],changed_returns=check['changed_getter_calls'],unchanged_finite=check['getter_calls']-check['changed_getter_calls'],excluded_fringe_calls=int(r['special']),changed_fraction_finite=check['changed_getter_calls']/check['getter_calls'],improved_returns='unmeasured: no physical reference'))
 alignment=O/'coverage_trace_alignment.json'
 if alignment.exists():
  a=json.loads(alignment.read_text());assert a['status']=='PASS'
  assert sum(r['finite_getter_calls'] for r in coverage)==a['finite_calls']
  for r in coverage:r.update(changed_fraction_all_matched_getters=r['changed_returns']/r['all_two_getter_calls'],trace_identity_alignment='PASS')
 write('coverage_accounting.csv',coverage)
 costs=rows('results/pex_kernel_revision/deployment_summary.csv');write('timing_breakdown_full_support.csv',costs)
 reuse=[]
 for r in costs:
  if r['method'] not in ['binary','full']:continue
  # Pure model: same cached rule/support/policy, mean measured per-design extraction.
  prep=float(r['external_cold_prep_s']) if 'external_cold_prep_s' in r else None
  # Preserve original field names and do not silently invent time boundaries.
  if prep is None:
   key=next(k for k in r if 'prep' in k and k.endswith('_s'));prep=float(r[key])
  for n in [1,10,100]:
   ex=float(r['extract_mean_s'])+float(r['process_residual_s'])
   reuse.append(dict(case=r['case'],method=r['method'],N_reuse=n,reusable_prep_s=prep,per_design_native_path_s=ex,modeled_total_s=prep+n*ex,scope='modeled PEX plus process residual and charged preparation; identical rule/support/policy cache; common layout/libs, SPEF/STA excluded; N=10/100 not measured'))
 write('reuse_cost_model.csv',reuse)
 # Original downstream tradeoffs are seed means, not pooled endpoints.
 ds=rows('results/dac_characterization_20261114/summary/downstream_means.csv');ix={(r['case'],r['budget'],r['method']):r for r in ds};summary={}
 for key in ['net_cap_nrmse','ws_abs_ns','slack_p99_ns']:
  diffs=[float(r[key])-float(ix[(r['case'],r['budget'],'binary')][key]) for r in ds if r['method']=='full'];summary[key]=dict(full_wins=sum(x<0 for x in diffs),binary_wins=sum(x>0 for x in diffs),ties=sum(x==0 for x in diffs),differences=diffs)
 (O/'rule_export_variant_check.json').write_text(json.dumps(summary,indent=2))
 raw=rows('results/dac_characterization_20261114/summary/downstream_raw.csv');absolute=[]
 for case,b in sorted({(r['case'],int(r['budget'])) for r in raw}):
  vals=[]
  for metric in ['net_cap_rmse_native','ws_abs_ns','slack_p99_ns']:
   for method in ['cmi','binary','full']:
    rr=[r for r in raw if r['case']==case and int(r['budget'])==b and r['method']==method];assert len(rr)==3
    u=json.loads(rr[0]['cap_unit']);factor=float(u[0])*{'PF':1000,'FF':1}[u[1].upper()] if metric=='net_cap_rmse_native' else 1000
    vals.append(f'{np.mean([float(r[metric]) for r in rr])*factor:.5g}')
  absolute.append([case.replace('ihp-sg13g2','IHP').replace('sky130hs','Sky'),str(b),*vals])
 tex='\n'.join([r'\begin{tabular}{llrrrrrrrrr}',r'\toprule',r'Layout & $B$ & MLI C & Binary C & Full C & MLI WS & Binary WS & Full WS & MLI P99 & Binary P99 & Full P99 \\',r'\midrule',*[' & '.join(x)+r' \\' for x in absolute],r'\bottomrule',r'\end{tabular}'])+'\n'
 (P/'tables/rule_export_absolute.tex').write_text(tex)
 # Training source/config/weights and actual candidate selection receipts.
 manifest={};models=read('configs/paper_models.json')
 for d,cfg in models.items():
  for c in cfg['checkpoints']:
   p=R/c['path'];assert sha(p)==c['sha256'];manifest[str(p)]=c['sha256']
  for p in [R/cfg['cohort'],R/'experiments/dac_characterization_20261114'/f'selected_{d}.json']:
   manifest[str(p)]=sha(p)
 deps=set()
 for x in __import__('re').findall(r'\\(?:input|includegraphics)(?:\[[^\]]*\])?\s*\{([^}]+)\}',(P/'main.tex').read_text()):
  p=P/x
  if not p.exists():p=R/'paper'/x
  if p.is_file():deps.add(p)
 for p in deps|{P/'main.tex',P/'references.bib',P/'main.bbl'}:manifest[str(p)]=sha(p)
 (O/'dependency_manifest.json').write_text(json.dumps(manifest,indent=2))
 print('counts',mapping);print('rule-export',summary);print('coverage',sum(r['changed_returns'] for r in coverage),sum(r['finite_getter_calls'] for r in coverage))
if __name__=='__main__':main()
