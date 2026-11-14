"""Verify manuscript artifacts and existing-record arithmetic, never run models."""
from pathlib import Path
import json,hashlib,subprocess,re,csv,math
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(p.open()))
for path,h in json.loads((P/'INPUT_SHA256.json').read_text()).items():assert sha(R/path)==h,path
m=rows(P/'tables/fixed_missingness.csv');assert len(m)==15
assert sum(float(r['full'])<float(r['cmi']) for r in m)==15
assert sum(float(r['full'])<float(r['binary']) for r in m)==13
assert all(float(r['full'])<float(r['binary']) for r in m if r['domain']=='reference')
# Validate printed missingness entries against the final CSV and original source summary.
summary=json.loads((R/'experiments/paper_controls/comparison_summary.json').read_text())
for r in m:
 for name in ['full','binary','residual','affine','anchor']:assert abs(float(r[name])-summary[r['domain']][name][r['condition']])<1e-12
budget=rows(P/'tables/fixed_budget_all.csv');original=rows(R/'review/dac_capacitance_20261114/same_budget.csv')
for a,b in zip(budget,original):
 assert (a['setting'],a['method'],a['budget'])==(b['setting'],b['method'],b['budget'])
 assert abs(float(a['macro_nrmse'])-float(b['macro_nrmse']))<1e-14
assert len(budget)==len(original)
# Native comparisons across same 16 layout/budget cells.
native=rows(P/'tables/native_budget.csv');lookup={(r['case'],r['budget'],r['method']):r for r in native};cells={(r['case'],r['budget']) for r in native};assert len(cells)==16
wins={}
for base in ['cmi','binary']:
 for metric in ['net_cap_nrmse','ws_abs_ns','slack_p99_ns']:
  wins[base+'/'+metric]=sum(float(lookup[c,b,'full'][metric])<float(lookup[c,b,base][metric]) for c,b in cells)
assert wins=={'cmi/net_cap_nrmse':16,'cmi/ws_abs_ns':16,'cmi/slack_p99_ns':16,'binary/net_cap_nrmse':6,'binary/ws_abs_ns':4,'binary/slack_p99_ns':6}
worst=max((float(lookup[c,b,'full']['slack_p99_ns'])-float(lookup[c,b,'binary']['slack_p99_ns']))*1000 for c,b in cells);assert abs(worst-7.6432866666667)<1e-9
info=subprocess.check_output(['pdfinfo',str(P/'main.pdf')],text=True);assert re.search(r'Pages:\s+7\b',info);assert re.search(r'Author:[ \t]*\n',info)
plain=subprocess.check_output(['pdftotext','-layout',str(P/'main.pdf'),'-'],text=True);pages=[p for p in plain.split('\f') if p.strip()];assert len(pages)==7
assert pages[6].lstrip().startswith('R EFERENCES');assert 'VI. C ONCLUSION' in pages[5]
assert not any('R EFERENCES' in p for p in pages[:6])
log=(P/'main.log').read_text();assert not re.search(r'Overfull|undefined|LaTeX Warning',log,re.I)
fonts=subprocess.check_output(['pdffonts',str(P/'main.pdf')],text=True);assert 'Type 3' not in fonts
src=(P/'main.tex').read_text();abstract=src.split(r'\begin{abstract}')[1].split(r'\end{abstract}')[0];words=len(abstract.split());assert 90<=words<=115
for bad in ['COMPLETION_ACCURACY_ONLY','INCONCLUSIVE_IMPLEMENTATION','closeout','legacy data','archived evidence','go/no-go','7334799','guoruiyuan','GRYYYYYYY']:
 assert bad not in src,bad
old=(P/'DAC_REWRITE.md').read_bytes();subprocess.run(['python3',str(P/'sync_markdown.py')],check=True);assert (P/'DAC_REWRITE.md').read_bytes()==old
report={'status':'passed','body_pages':6,'references_only_pages':1,'font':'IEEEtran 10pt','pdf_author_empty':True,'abstract_words':words,'missingness_conditions':len(m),'unrounded_original_summary_match':True,'budget_rows_matched':len(budget),'native_cells':len(cells),'native_full_wins':wins,'worst_binary_p99_delta_ps':worst,'source_sync':True,'overfull_boxes':0,'undefined_references':0,'type3_fonts':False,'new_model_or_solver_calls':0,'starting_commit':'7334799ce7ca2e46dc4b4091b470cfc3af8c5cc7','main_reference_commit':'05d0717c31c3ebd38107c846cfa7712913078027'}
(P/'VERIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
