"""Insert measured continuation into the authoritative manuscript, idempotently."""
from common_runtime import *
import re
P=R/'paper/dac_layout_query_revision'
def main():
    assert read(O/'CHECKS.json')['passed']
    rows=list(csv.DictReader((O/'accuracy_runtime.csv').open()));get=lambda m,b=32:next(r for r in rows if r['task']=='fem' and r['method']==m and int(r['batch_limit'])==b)
    f,b,a,mlp,ac=[get(m) for m in ['full','binary','anchor','mlp_adapt','attentioncap_adapted']]
    sol=read(O/'solver_task_match.json');ns=read(O/'native_kernel_summary.json');flow=list(csv.DictReader((O/'native_flow_summary.csv').open()));rat=[float(r['extraction_ratio']) for r in flow if r['method']=='full'];prep=read(O/'rule_preparation.json')
    costs={m:next(r['prediction_all_platforms']['wall_s'] for r in prep['rows'] if r['method']==m)+sum(r['export']['wall_s'] for r in prep['rows'] if r['method']==m)+next(r['payload_write']['wall_s'] for r in prep['rows'] if r['method']==m) for m in ['cmi','binary','full']}
    shared=sum(prep[k]['wall_s'] for k in ['data_load','shared_model_bundle_load','support_selection']);mantissa,exponent=f"{sol['max_column_scaled_error']:.1e}".split('e')
    section=rf'''% BEGIN RUNTIME_ADDENDUM
\subsection{{Accuracy--Runtime Trade-offs and Deployment Cost}}
We measure the same queries on one pinned Xeon Gold 6530 CPU thread,
with three warmups and 20 randomized timing blocks. Each batch limit
$Q\in\{{1,8,32\}}$ has separately evaluated predictions. Times include
query encoding, numerical candidates, all three ensemble members, and output
assembly; support and material tokens are excluded from the query denominator.
Table~\ref{{tab:offgrid}} and Fig.~\ref{{fig:runtime}} pair error with measured cost.
For the 71 templates, Full's warm amortized cost is
{float(f['amortized_wall_ms']):.3f}\,ms/query, versus {float(b['amortized_wall_ms']):.3f} for Binary
and {float(a['amortized_wall_ms']):.3f} for Anchor. Full's actual single-request mean
is {float(get('full',1)['batch_mean_ms']):.2f}\,ms; throughput does not imply this latency.

Retaining each fixed-support fit reduces adapted MLP's warm cost to
{float(mlp['amortized_wall_ms']):.3f}\,ms/query, with NRMSE {float(mlp['macro_nrmse']):.5f};
its one-time six-context fit costs {float(mlp['fit_once_all_contexts_wall_s']):.2f}\,s,
including first-use optimizer initialization. Adapted AttentionCap costs
{float(ac['amortized_wall_ms']):.3f}\,ms/query but has NRMSE {float(ac['macro_nrmse']):.5f}
on these same templates; its source-selected adaptation costs
{float(ac['fit_once_all_contexts_wall_s']):.2f}\,s. No query labels enter either fit.
Transformer support states are not cached: changing $Q$ changes its predictions.
Anchor/CMI remain more accurate than Full with this full support.

A resident one-RHS P2 solve takes {sol['resident_mean_total_wall_s']/71:.3f}\,s/query,
including a regenerated fine mesh, assembly, factorization and both nonzero
outputs. Three passes match the certified full-matrix target row within
{sol['max_column_scaled_error']:.1e} relative scale. Cold fine-only solving and
three-level certification cost {sol['cold_fine_wall_s']:.1f} and
{sol['cold_certification_wall_s']:.1f}\,s over these 71 geometries, respectively.
Surrogate errors exceed reference uncertainty; these are not equal-accuracy
speedup claims.

For native agreement, a validated C++ finite-distance getter counterpart takes
{ns['mean_ns']:.2f}\,ns/query in long warm loops after width/context resolution;
the ctypes calling loop takes {ns['ctypes_mean_ns']/1000:.3f}\,$\mu$s/query.
Neither measures a complete PEX query. In 96 release-OpenROAD runs (eight
unchanged layouts, four rule variants, three repeats), Full's extraction-time
ratio to original rules ranges from {min(rat):.3f} to {max(rat):.3f}.
At $B=8$, seed 11, prediction and export for all four libraries cost
{costs['cmi']:.2f}/{costs['binary']:.2f}/{costs['full']:.2f}\,s for CMI/Binary/Full,
plus shared input, support and model loading. Each library serves two measured
designs. SPEF writing and STA are timed separately; rule parsing remains in
extraction. The exported electrical results match the frozen variants exactly.
This configuration keeps learned inference outside the native extraction loop;
it establishes neither added-node enrichment nor online model replacement.
% END RUNTIME_ADDENDUM
'''
    shortsection=rf'''% BEGIN RUNTIME_ADDENDUM
\subsection{{Accuracy--Runtime Trade-offs and Deployment Cost}}
On one pinned Xeon Gold 6530 thread, three warmups precede 20 randomized
timing blocks. Each Q limit (1/8/32) has its own scored predictions.
Warm times include encoding, numerical candidates, three learned members and
assembly; only requested geometries enter the denominator.
At Q limit 32, Full/Binary/Anchor cost
{float(f['amortized_wall_ms']):.3f}/{float(b['amortized_wall_ms']):.3f}/{float(a['amortized_wall_ms']):.3f}\,ms/query
(Table~\ref{{tab:offgrid}}, Fig.~\ref{{fig:runtime}}).
Full's measured single-request mean is {float(get('full',1)['batch_mean_ms']):.2f}\,ms.

With support fits retained, adapted MLP costs {float(mlp['amortized_wall_ms']):.3f}\,ms/query
at NRMSE {float(mlp['macro_nrmse']):.5f}; its six-context fit costs
{float(mlp['fit_once_all_contexts_wall_s']):.2f}\,s including first-use optimizer initialization.
Adapted AttentionCap costs {float(ac['amortized_wall_ms']):.3f}\,ms/query, but its NRMSE is
{float(ac['macro_nrmse']):.5f}, with {float(ac['fit_once_all_contexts_wall_s']):.2f}\,s adaptation.
Neither fit accesses query labels. Query-dependent Transformer support states
are not cached. Anchor/CMI are more accurate than Full here.

Resident one-RHS fine P2 solving costs {sol['resident_mean_total_wall_s']/71:.3f}\,s/query,
including remeshing, assembly, factorization and both nonzero outputs.
All 213 solves match certified full-matrix target rows within
${mantissa}\times10^{{{int(exponent)}}}$ relative scale. Certification cost is separate;
surrogate errors exceed reference uncertainty, precluding an equal-accuracy
speedup claim. A validated C++ finite-distance getter counterpart costs
{ns['mean_ns']:.2f}\,ns/query in warm loops after width/context resolution
({ns['ctypes_mean_ns']/1000:.3f}\,$\mu$s through ctypes), not a complete PEX query.

Across 96 release runs, Full's extraction/original ratio is
{min(rat):.3f}--{max(rat):.3f}. Fixed-node prediction/export for four libraries
at B=8, seed 11 costs {costs['cmi']:.2f}/{costs['binary']:.2f}/{costs['full']:.2f}\,s
for CMI/Binary/Full, plus {shared:.2f}\,s shared loading/support preparation.
Each library serves two measured layouts. SPEF writing and STA are separate;
rule parsing remains in extraction. Electrical results match the frozen
variants exactly. This offline configuration keeps learned inference outside
the native extraction loop.
% END RUNTIME_ADDENDUM
'''
    fig=r'''\begin{figure*}[t]
\centering\includegraphics[width=\textwidth]{figures/runtime_accuracy.pdf}
\caption{Accuracy and deployment cost. (a) Same 71 templates; circles/squares/triangles denote Q limits 32/8/1, each with its own error. Y is linear below 0.001 and logarithmic above; the fine-FEM point measures agreement with the fine reference, not zero discretization error. (b) Three-run mean per-layout extraction ratios; bars mark medians. (c) Fixed-node B=8, seed-11 prediction/export for four libraries. Shared setup and adaptation are separate. Panels (b,c) use controlled support; panel (a) uses all S.}
\label{fig:runtime}
\end{figure*}
'''
    extra=r'''\begin{table*}[t]
\centering\caption{CPU query timing on the same 71 FEM templates. Warm ms/Q uses actual batch sizes with a maximum of 32; Q=1 mean/P95 are measured request latencies in ms. Fit is the one-time total for six support contexts, including first-use optimizer initialization. All neural results use three members; loading is reported separately. Complete component MAE/P95/P99 and per-block variation are in the reproduction CSVs.}
\label{tab:runtime_detail}\small\input{tables/runtime_detail.tex}
\end{table*}
\begin{figure*}[t]
\centering\includegraphics[width=.8\textwidth]{figures/runtime_native_agreement.pdf}
\caption{Separate native-agreement runtime comparison on all 480 queries. Each method has independently scored Q limits 1, 8 and 32. The validated C++ counterpart reproduces the reference by construction, after width/context resolution. This is interface agreement, not a physical error ranking.}
\label{fig:runtime_native}
\end{figure*}
'''
    for name in ['main.tex','extended.tex']:
        path=P/name;text=path.read_text()
        chosen_section=shortsection if name=='main.tex' else section
        if '% BEGIN RUNTIME_ADDENDUM' in text:
            text=re.sub(r'% BEGIN RUNTIME_ADDENDUM.*?% END RUNTIME_ADDENDUM\n',lambda m:chosen_section,text,flags=re.S)
        else:
            # Replace the single-pass cost illustration with the repeated study.
            if name=='main.tex':
                text=re.sub(r'Thus evaluation is batch-conditioned\. Mean three-member FEM-batch wall times.*?no end-to-end speedup follows\.', 'Thus evaluation is batch-conditioned.',text,flags=re.S)
            else:
                text=re.sub(r'This is batch-conditioned query evaluation\. Mean three-member.*?(?=\\subsection\{Discussion\})','This is batch-conditioned query evaluation.\n\n',text,flags=re.S)
            text=text.replace(r'\subsection{Discussion}',chosen_section+'\n'+r'\subsection{Discussion}')
        if r'\label{fig:runtime}' not in text:text=text.replace('% BEGIN RUNTIME_ADDENDUM',fig+'\n% BEGIN RUNTIME_ADDENDUM')
        if name=='main.tex':
            text=text.replace('These evaluations separate native agreement from physical reference error.','These evaluations separate native agreement from physical error and distinguish query computation, rule preparation, and native extraction cost.')
            # Place the double-column float at the census insertion point;
            # declaring it only after the final subsection forces a spare page.
            text=re.sub(r'\\begin\{figure\*\}\[t\]\n\\centering\\includegraphics\[width=\\textwidth\]\{figures/runtime_accuracy.pdf\}.*?\\end\{figure\*\}\n','',text,flags=re.S)
            marker='% RUNTIME_FLOAT_ANCHOR'
            assert marker in text
            text=text.replace(marker,marker+'\n\n'+fig)
            text=re.sub(r'\\begin\{figure\*\}\[t\]\n\\centering\\includegraphics\[width=\\textwidth\]\{figures/query_census.pdf\}.*?\\end\{figure\*\}\n','',text,flags=re.S)
            text=text.replace(r'\input{tables/offgrid.tex}',r'\input{tables/offgrid_runtime.tex}')
            old='Weighted FEM uses occurrence counts divided by sampling probability. Native agreement and direct physical error have different references and units; compare methods only within a column.'
            new='FEM$_w$ weights occurrences by inverse sampling probability. The last column is warm FEM wall ms/query on one CPU thread, with Q limit 32 and three learned members; fitting/loading is separate. AC is adapted AttentionCap. Native agreement and physical error have distinct references; compare within a column.'
            text=text.replace(old,new)
        elif r'\label{tab:runtime_detail}' not in text:text=text.replace('% END RUNTIME_ADDENDUM','% END RUNTIME_ADDENDUM\n'+extra)
        path.write_text(text)
    write(O/'PAPER_VALUES.json',dict(main_sha256=sha(P/'main.tex'),extended_sha256=sha(P/'extended.tex'),query=get('full'),native_extraction_ratio_range=[min(rat),max(rat)],four_library_predict_export_seconds=costs,solver=sol,native_kernel=ns))
if __name__=='__main__':main()
