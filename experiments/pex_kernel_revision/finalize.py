"""Completed evidence, finite resource ledger and manuscript integrity."""
from common import *
import collections,subprocess,re,math
P=R/'paper/dac_layout_query_revision';D=R/'docs/pex_kernel_revision'
s=read(O/'SUMMARY.json');native=list(csv.DictReader((O/'native_flow_timing.csv').open()));inv=list(csv.DictReader((O/'support_coverage_inventory.csv').open()));pre=read(O/'preparation.json');checks=read(O/'pass_through.json')
assert len(native)==120 and len(inv)==21840 and checks['passed']
assert {float(r['requested_holdout']) for r in inv}=={.1,.3,.5,.7}
assert all(read(O/p)['passed'] for p in ['kernel_unit_tests.json','physical_checks.json','coverage_reuse_checks.json','extracted_native_validation.json','pinned_storage_retrieval_checks.json'])
for case in {r['case'] for r in native}:
 for method in ['original','disabled','pass','binary','full']:
  rr=[r for r in native if r['case']==case and r['method']==method];assert {int(r['block']) for r in rr}=={0,1,2};assert len({r['electrical_sha256'] for r in rr})==1
  if method in ['original','disabled','pass']:assert all(r['identical_native']=='True' for r in rr)
  else:assert all(int(r['changed'])>0 for r in rr)
  for r in rr:
   rec=read(O/'native'/case/method/r['block']/'receipt.json');assert rec['comparison']['metrics']['resistance']['nrmse']==0
   if method in ['pass','binary','full']:
    expected=next(a['slots'] for a in pre['rows'] if a['platform']==case.split('/')[0] and a['method']==method);assert int(r['applied'])==expected,(case,method,r['applied'],expected)
# Every process resource file is counted once, including retained failed/preflight runs.
resources=[]
for p in sorted(O.rglob('resource.txt')):
 text=p.read_text();user=re.search(r'User time \(seconds\): ([\d.]+)',text);sysm=re.search(r'System time \(seconds\): ([\d.]+)',text)
 if user and sysm:resources.append(dict(path=str(p.relative_to(R)),cpu_s=float(user[1])+float(sysm[1])))
builds=[]
for p in [O/'build/attempt1/receipt.json',O/'build/receipt.json']:
 if p.exists():builds.append(dict(path=str(p.relative_to(R)),cpu_s=read(p)['cpu_s']))
other=[]
for p in sorted(O.glob('coverage_*_receipt.json')):
 other.append(dict(path=str(p.relative_to(R)),cpu_s=read(p)['cpu_s']))
for name in ['physical_checks.json','preparation_preflight.json','preparation.json']:
 p=O/name
 if p.exists():other.append(dict(path=str(p.relative_to(R)),cpu_s=read(p)['cpu_s']))
p=O/'inventory_cost_before_path_separation.csv'
if p.exists():other.append(dict(path=str(p.relative_to(R)),cpu_s=sum(float(r['cpu_s']) for r in csv.DictReader(p.open())),scope='earlier inventory timing survives in raw CSV; its diagnostic resource paths were later overwritten by validation before path separation'))
core_hours=sum(r['cpu_s'] for r in resources+builds+other)/3600;allowance=.5;assert core_hours+allowance<16
ledger=dict(measured_cpu_core_hours=core_hours,auxiliary_allowance_core_hours=allowance,budget_charge_core_hours=core_hours+allowance,budget_core_hours=16,maximum_compute_workers=4,new_training_steps=0,new_field_solves=0,gpu_seconds=0,native_processes=resources,builds=builds,other=other,allowance_scope='Conservative allowance, not measured runtime: initial compiler failure, imports, numerical unit checks, short failed pilot, native Python trace/SPEF comparison and orchestration, metadata/plot/TeX/packaging, supervisor work. Prior task ledger excluded.')
write(O/'RESOURCE_LEDGER.json',ledger)
for file in ['main','extended']:
 log=(P/(file+'.log')).read_text();assert 'Overfull' not in log and 'undefined' not in log
sync=read(P/'SOURCE_SYNC.json')
for name,key in [('main.tex','main_tex_sha256'),('main.pdf','compiled_pdf_sha256'),('DAC_REWRITE.md','reading_md_sha256')]:assert sha(P/name)==sync[key]
for name,h in sync['rendered_inputs'].items():assert sha(P/name)==h
pdfs={name:int(re.search(r'Pages:\s+(\d+)',subprocess.check_output(['pdfinfo',str(P/(name+'.pdf'))],text=True))[1]) for name in ['main','extended']}
write(O/'CHECKS.json',dict(passed=True,coverage_episodes=len(inv),all_four_ratios=True,exact_prior_Full_Binary_30percent=True,physical_queries=71,native_kernel_returns=480,native_runs=len(native),pass_through=True,resistance_unchanged=True,payload_applied_counts_exact=True,PDF_pages=pdfs,budget_passed=True))
levels=dict(production_kernel_comparison='completed: pinned extracted OpenRCX function bodies plus specified MLI; no commercial binary execution',same_physical_reference='completed: 71 full-support symmetric 2D templates, including learned slot generation and native retrieval',coverage_sensitivity='completed: 21,840 paired episodes, 10/30/50/70%, all intended domains/conditions',compute_table_injection='completed: original/disabled/native pass-through/Binary/Full; full original rules unchanged',grid_reuse='completed: whole eligible grids identical across two designs/process',fixed_node_export='separate completed B8 path reused from runtime_accuracy_20261115',online_neural_inference='not implemented; inference occurs during preparation',native_calibration_to_FEM_alignment='not claimed; native fidelity and template physics separate',commercial_xRC='not run; supplied core mathematics only')
write(O/'COMPLETION_LEVELS.json',levels)
phys={r['method']:r for r in s['physical']};dep=[r for r in s['deployment'] if r['method']=='full'];ratio=[r['extract_ratio'] for r in dep];cold=[r['cold_PEX_overhead'] for r in dep]
lines=['# Completed PEX kernel and compute-table results','',f'Continuation of `a519539fee8a763c74e1db61427fdd02d85511ca`. Main PDF: {pdfs["main"]} pages; expanded PDF: {pdfs["extended"]} pages.','', '## Shared physical support','', '| Method | NRMSE | P95 absolute (pF/m) |','|---|---:|---:|']
for m in ['mli','openrcx_ideal','openrcx_kernel','anchor','binary','full','binary_compute','full_compute']:lines.append(f'| {m} | {phys[m]["macro_nrmse"]:.5f} | {phys[m]["p95_nonzero_F_per_m"]*1e12:.3f} |')
lines+=['','The same 71 full-support templates are independently referenced, not exact arbitrary layout sections. Native width mapping is retained in both OpenRCX variants; the ideal variant removes distance quantization only. Direct learned queries and whole-slot generation have distinct Q protocols. Full populated-table error exceeds the native kernel on this cohort. No query-error-selected fallback hides that result.','', '## Coverage and native deployment','',f'All 21,840 shared-support/query episodes cover the complete 10/30/50/70% sweep. Full/Binary 30% scores match their prior results exactly. The source-selected numerical GP and actual anchor remain controls. Complete-cell MLI, sparse/boundary extensions, actual support counts and rounded duplicate episodes are separately recorded.','',f'The new internal interface prepares {sum(r["injected_slots"] for r in pre["platforms"]):,} slots. Native-value pass-through preserves getters and electrical SPEF; learned returns match payloads, resistance and uncovered returns are unchanged. The 120 release runs cover all eight layouts, five modes and three repetitions. Full extraction ratios range {min(ratio):.3f}–{max(ratio):.3f}; first-design PEX overhead including explicit preparation is {min(cold)*100:.1f}–{max(cold)*100:.1f}%. This is separate from the existing fixed-node 0.983–1.047 result.','', '| Layout | Full extraction ratio | Full net-C NRMSE | Worst-slack delta (ps) | Cold PEX overhead |','|---|---:|---:|---:|---:|']
for r in dep:lines.append(f'| {r["case"]} | {r["extract_ratio"]:.3f} | {r["net_C_nrmse"]:.5f} | {r["worst_slack_delta_ps"]:+.4f} | {r["cold_PEX_overhead"]*100:.1f}% |')
lines+=['','Cold per-library numbers include a full model load and the inventory extraction required by deferred rule loading. Process residual includes startup/payload parsing and shutdown. SPEF and STA are separate, not denominators used to dilute PEX overhead. Small ratios below 1 are not claimed stable speedups. Native reference error is fidelity, not independent electrostatic error.','',f'New measured compute: {core_hours:.3f} CPU core-hours; conservative auxiliary allowance {allowance:.2f}; total charge {core_hours+allowance:.3f}<16. No new source training, GPU, or physical reference solves.','', '## Completion levels','']+[f'- **{k}**: {v}.' for k,v in levels.items()]
(D/'RESULTS.md').write_text('\n'.join(lines)+'\n')
(D/'REVIEW_AND_CHANGES.md').write_text('''# Six proposal changes and evidence

| Request | Implemented manuscript position | Evidence |
|---|---|---|
| Production-related kernels as primary comparators | II-C, V-A/V-B; production-kernel table | baseline_contracts.json, kernel_unit_tests.json, extracted_native_validation.json; MLI mathematical implementation, no commercial execution |
| Numerical methods as component analysis without deleting strong controls | III-A, V-B; compact control table; expanded original controls | source-selected GP and actual Anchor; all prior numerical/budget tables retained |
| Preserve task-adapted learning comparisons | II-D, IV, V-B/V-D; expanded learning tables | unchanged MLP/CNP/AttentionCap identities, support and update counts; no universal impossibility claim |
| Populate actual internal compute tables and measure new path | III-B and V-C; new deployment table | pinned source patch, pass_through.json, physical_checks.json,120 release runs; fixed-node export separately named |
| Move query distribution to Section II | II-B, fig:census in both sources | query_census_by_layout.csv; raw/effective and finite/all denominators explicit |
| Retain all10/30/50/70% coverage levels | V-A, fig:coverage; three expanded complete tables | support_coverage_results.csv plus per-episode inventory; same S/Q and duplicate handling |

The corrected native getter semantics and supplied MLI core are distinct from complete commercial products. All source/model identities remain frozen. No new candidate or selection rule is tuned on the physical confirmation labels. The new title is conditioned on completed internal injection, not borrowed from fixed-node export.
''')
print('final checks passed; pages',pdfs,'new CPU hours',round(core_hours,3))
