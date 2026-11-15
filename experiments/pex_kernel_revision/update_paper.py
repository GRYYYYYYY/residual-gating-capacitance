"""Publish only completed measurements into main and extended sources."""
from common import *
import re,subprocess
P=R/'paper/dac_layout_query_revision';T=P/'tables'
assert read(O/'pass_through.json')['passed']
assert read(O/'physical_checks.json')['passed']
assert read(O/'native_completed.json')['runs']==120
s=read(O/'SUMMARY.json');phys={r['method']:r for r in s['physical']};scores=list(csv.DictReader((O/'support_coverage_scores.csv').open()));inv=list(csv.DictReader((O/'support_coverage_inventory.csv').open()))
common=[r for r in scores if r['population']=='common' and r['regime']!='complete_cell'];idx={(r['domain'],r['requested_holdout'],r['regime'],r['protocol'],r['method']):float(r['macro_nrmse']) for r in common}
wins={m:sum(v<idx[k[:-1]+(m,)] for k,v in idx.items() if k[-1]=='full' and k[:-1]+(m,) in idx) for m in ['openrcx_kernel','mli_sparse','binary']}
total=sum(k[-1]=='full' for k in idx)
valid=sum(r['openrcx_applicable']=='True' for r in inv);allq=sum(int(r['query_count']) for r in inv);fullcell=sum(int(r['complete_cell_queries']) for r in inv);dups=sum(r['duplicate_of']!='null' for r in inv)
(T/'coverage_findings.tex').write_text(f'Figure~\\ref{{fig:coverage}} includes all {total} domain--holdout--condition cells. Full has lower error than the OpenRCX kernel, MLI with the explicit extension, and Binary in {wins["openrcx_kernel"]}, {wins["mli_sparse"]}, and {wins["binary"]} cells, respectively. The kernels share {valid:,}/{len(inv):,} feasible support/query episodes. Complete MLI cells cover {fullcell/allq*100:.1f}\\% of requested queries across the sweep; the remainder use the declared boundary or sparse-support extension. The inventory flags {dups:,} repeated rounded S/Q episodes rather than treating them as additional independent evidence. Detailed cells and all numerical controls are retained in the expanded tables.\n')
(T/'kernel_findings.tex').write_text(f'Table~\\ref{{tab:production}} drives both production-related kernels with the same FEM-characterized samples. Specified MLI obtains NRMSE {phys["mli"]["macro_nrmse"]:.5f}; the mapped/quantized OpenRCX kernel obtains {phys["openrcx_kernel"]["macro_nrmse"]:.5f}. Its ideal continuous-distance counterpart obtains {phys["openrcx_ideal"]["macro_nrmse"]:.5f}, isolating one implementation effect without introducing width interpolation. Full/Binary values retrieved through populated compute tables obtain {phys["full_compute"]["macro_nrmse"]:.5f}/{phys["binary_compute"]["macro_nrmse"]:.5f}. Full does not improve over the native kernel on this complete-support cohort. These values use a complete-slot preparation protocol and native mapping, so direct-query errors cannot be substituted for them. Extracted pinned function bodies agree with the Python evaluator, and native-value pass-through preserves the kernel outputs.\n')
checks=read(O/'pass_through.json')['checks'];pre=read(O/'preparation.json');dep=[r for r in s['deployment'] if r['method']=='full'];ratio=[r['extract_ratio'] for r in dep];cold=[r['cold_PEX_overhead'] for r in dep];changed=sum(r['changed_getter_calls'] for r in checks if r['method']=='full');slots=sum(r['injected_slots'] for r in pre['platforms'])
(T/'compute_findings.tex').write_text(f'The new interface populates {slots:,} eligible finite slots across four rule libraries. Native-value pass-through preserves traced getter returns and electrical SPEF records on all eight layouts. Full changes {changed:,} traced returns; covered returns match injected values, and resistance/uncovered returns remain identical. Table~\\ref{{tab:deployment}} reports the newly measured path: across 120 release runs, the Full extraction/original ratio ranges from {min(ratio):.3f} to {max(ratio):.3f}. Including inventory, input/model/support preparation and process-startup residual, first-design PEX overhead ranges from {100*min(cold):.1f}\\% to {100*max(cold):.1f}\\%. SPEF output and STA are measured separately and are not used to dilute this denominator. Values below one are repeat-run variation, not a stable acceleration claim.\n')
marker='% PEX_KERNEL_REVISION_MAIN\n'
current=(P/'main.tex').read_text()
if marker in current:
 main=current
else:
 expected=subprocess.check_output(['git','show','a519539fee8a763c74e1db61427fdd02d85511ca:paper/dac_layout_query_revision/main.tex'],cwd=R,text=True)
 assert current==expected,'Preserve later main edits: initial migration requires the audited base source'
 main=marker+(H/'main_revision.tex.in').read_text();(P/'main.tex').write_text(main)
if marker in current and '% PEX_KERNEL_REVISION_EXTENDED' in (P/'extended.tex').read_text():
 print('updated measured inputs; preserved authoritative manuscript edits')
 raise SystemExit(0)
# Initial migration only; subsequent runs preserve the authoritative sources.
base=subprocess.check_output(['git','show','a519539fee8a763c74e1db61427fdd02d85511ca:paper/dac_layout_query_revision/extended.tex'],cwd=R,text=True)
base=base.replace('Characterization-Conditioned Capacitance Estimation for Rule-Based Parasitic Extraction','Learning to Populate Capacitance Evaluation Tables for Rule-Based Parasitic Extraction')
intro=main[main.index('\\section{Introduction}'):main.index('\\section{Problem and Related Work}')]
a=base.index('\\section{Introduction}');b=base.index('\\section{Problem and Related Work}');base=base[:a]+intro+base[b:]
abstract=main[main.index('\\begin{abstract}'):main.index('\\end{abstract}')+len('\\end{abstract}')];base=re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}',lambda m:abstract,base,flags=re.S)
base=re.sub(r'\\begin\{figure\*\}\[t\]\s*\\centering\\includegraphics\[width=\\textwidth\]\{figures/query_census.pdf\}.*?\\end\{figure\*\}', '',base,flags=re.S)
ii=main[main.index('\\section{Problem and Related Work}'):main.index('\\section{Estimator and Compute-Table Preparation}')]
a=base.index('\\section{Problem and Related Work}');b=base.index('\\section{Characterization-Conditioned Estimator}',a);base=base[:a]+ii+base[b:]
method_float=re.search(r'\\begin\{figure\*\}\[!t\].*?figures/method.pdf.*?\\end\{figure\*\}',base,re.S)
if method_float:
 block=method_float.group(0);base=base[:method_float.start()]+base[method_float.end():];base=base.replace('\\section{Characterization-Conditioned Estimator}', '\\section{Characterization-Conditioned Estimator}\n'+block,1)
newmethod=main[main.index('\\subsection{Populating the native evaluation structure}'):main.index('\\section{Experimental Setup}')]
base=base.replace('\\section{Experimental Setup}',newmethod+'\n\\section{Experimental Setup}',1)
extra=r'''
\section{Production Kernels and Internal Compute-Table Deployment}
\subsection{Coverage sensitivity over all four holdouts}
\input{tables/coverage_findings.tex}
\begin{figure*}[t]\centering\includegraphics[width=\textwidth]{figures/coverage_four_ratios.pdf}
\caption{All four characterization holdouts on common feasible S/Q. Complete-cell and sparse-support-extension coverage is recorded independently of errors.}\label{fig:coverage}\end{figure*}
'''
for domain,name in [('public','Public rules'),('reference','FEM'),('to_asap7','Transfer')]:
 extra+=r'\begin{table*}[t]\centering\caption{'+name+r': complete four-holdout sensitivity, mean-mask macro NRMSE. MLI-ext. includes declared sparse/boundary extensions; ORCX includes native mapping and quantization. Selected GP is source-validation-frozen.}\small\input{tables/coverage_'+domain+r'.tex}\end{table*}'+'\n'
extra+=r'''
\subsection{Same-physics kernel and generated-table evaluation}
\input{tables/kernel_findings.tex}
\begin{table}[t]\centering\caption{Production-related kernel evaluation on the same 71 independently referenced templates.}\label{tab:production}\small\input{tables/production_kernels.tex}\end{table}
\begin{table}[t]\centering\caption{Full-support numerical and conditional controls; reused warm runtime.}\label{tab:components}\small\input{tables/kernel_components.tex}\end{table}
The scalar projection wrapper does not claim equivalence between native calibration materials and the FEM stack. Its third output channel carries the declared diagonal template projection; it is not a native resistance measurement. Rank-four MLI is tested on known multilinear functions only. The production injection retains native resistance without using that scalar wrapper.
\subsection{New computeTable measurements}
\input{tables/compute_findings.tex}
\begin{table}[t]\centering\caption{New Full compute-table deployment: net-C fidelity, mean extraction ratio and cold external preparation.}\label{tab:deployment}\small\input{tables/compute_deployment.tex}\end{table}
The new release build leaves getters unchanged. The preparation hook updates coupling/fringe only after native table construction; a separate trace build validates every covered return. Entire special-tail and diagonal tables remain native, as do measurement-bin conflicts and direct measure-table boundary returns. Inventories from both designs match within each process. The cache therefore enumerates the supported rule grid, rather than just the current design's requested slots.

Cold preparation charges the inventory extraction required by the pinned deferred-loading API, model loading, support mapping, inference and payload output. Full-model bundle loading is not claimed free for the first design. Per-process cold totals charge a complete load; the two-design reuse accounting charges it once per prepared library. Process residual is total wall minus named Tcl stages and includes startup/payload loading and shutdown, not an isolated parse benchmark. Native compute construction and hook application are measured within extraction. The detailed CSV separates these boundaries, PEX-only overhead, SPEF and STA; source training is separately reported and no training is repeated.

'''
extra+=r'''
\begin{table*}[t]\centering\caption{Supplied model cost: sum of three members' recorded final-stage training wall seconds, not parallel elapsed. Hardware and source-training opportunity differ; these are provenance costs, not matched speed rankings. Missing receipts are shown as --. Initialization, source-label generation and model selection are not fully aggregated, so complete training cost is unavailable.}\label{tab:sourcecost}\small\input{tables/source_training_costs.tex}\end{table*}
The common 918 physical support geometries have recorded fine-solver CPU cost 4,889.83\,s, or 11,761.63\,s for three-level certification. These supplied-input costs are not charged per query and are not new computation. Public rule characterization cost is unavailable.
\begin{table*}[t]\centering\caption{Complete new compute-table pipeline: three runs per layout/mode. PEX, its sample SD, SPEF output, STA read/analysis and external cold preparation are wall seconds. Net-C error and slack difference use the original full-rule reference. Preparation is reusable within a process library; native table construction/injection remains inside PEX.}\label{tab:allstages}\small\input{tables/native_stages.tex}\end{table*}
'''
base=base.replace('\\section{Conclusion}',extra+'\n\\section{Conclusion}',1)
base=base.replace('The evidence here supports replay and fixed-grid rule export; node enrichment and online model substitution are not established.','The evidence supports query replay, fixed-node rule export and the separate internal compute-table injection evaluated below. Neural inference occurs during preparation; runtime getters remain native.')
base=base.replace('CMI is an explicit multilinear control.','CMI combines complete-cell multilinear interpolation with support-only sparse completion and clamping. Its extensions are distinct from the specified complete-cell core and are not attributed to a commercial implementation.')
base=base.replace('and native rule export. Experiments','and internal compute-table population as well as native rule export. Experiments')
ext_marker='% PEX_KERNEL_REVISION_EXTENDED\n'
if ext_marker not in (P/'extended.tex').read_text():
 expected=subprocess.check_output(['git','show','a519539fee8a763c74e1db61427fdd02d85511ca:paper/dac_layout_query_revision/extended.tex'],cwd=R,text=True)
 assert (P/'extended.tex').read_text()==expected,'Preserve later extended edits before applying migration'
 (P/'extended.tex').write_text(ext_marker+base)
print('updated main and extended from completed measurements')
