"""Check compiled manuscript dependencies, citations, layout log and text extraction."""
from pathlib import Path
import re,json,subprocess,hashlib
R=Path(__file__).resolve().parents[2];P=R/'paper/dac_layout_query_revision';O=R/'results/dac_main13_integrated_revision/main13_20261117'
src=(P/'main.tex').read_text();log=(P/'main.log').read_text();pdf=P/'main.pdf'
assert 'Output written on main.pdf' in log
bad=[line for line in log.splitlines() if re.search(r'Overfull|undefined references|Citation .* undefined|Reference .* undefined|Missing character',line)]
assert not bad,bad
required=['baseline_consistency','mechanism_controls','mli_strata','strong_numerical','numerical_30percent','native_sparse_accuracy','native_sparse_tails','native_sparse_absolute','native_sparse_cost','native_reuse_cost','rule_export_absolute']
for name in required:assert f'\\input{{tables/{name}.tex}}' in src and (P/f'tables/{name}.tex').exists(),name
text=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True);assert '\ufffd' not in text and '??' not in text
for term in ['Native-sparse','Binary','Full','C1','C2','C3','20.64','60/60','7/16','9/16']:assert term in text,term
info=subprocess.check_output(['pdfinfo',str(pdf)],text=True);pages=int(re.search(r'Pages:\s+(\d+)',info)[1])
(O/'tests/pdf_checks.json').write_text(json.dumps(dict(status='PASS',pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),main_source_sha256=hashlib.sha256((P/'main.tex').read_bytes()).hexdigest(),pages=pages,undefined_citations_or_references=False,overfull_boxes=False,missing_glyphs=False,required_generated_tables=required,text_extractable=True,scope='automatic compile/dependency/text checks; visual review recorded separately; no page-limit criterion'),indent=2))
(O/'raw').mkdir(exist_ok=True);(O/'raw/main_pdf_extracted.txt').write_text(text);print('PDF_CHECKS_PASS',pages,'pages')
