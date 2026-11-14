from pathlib import Path
import json,hashlib,csv,re,subprocess
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=json.loads((P/'INPUT_SHA256.json').read_text())
for p,h in refs.items():assert sha(ROOT/p)==h,p
body=(P/'DAC_REWRITE.md').read_text();assert body.index('## RQ1')<body.index('## RQ2')<body.index('## RQ3')<body.index('## References')
abstract=body.split('## Abstract')[1].split('## Introduction')[0];assert '0.1233' not in abstract and 'D[Full]' not in abstract
source=ROOT/'results/dac_characterization_20261114/summary/budget_curves.csv';lookup={(r['setting'],r['method'],int(r['budget'])):float(r['nrmse']) for r in csv.DictReader(source.open()) if r['strategy']=='farthest'}
block=body.split('| Setting | B | cmi |',1)[1].split('\n\n',1)[0];count=0
for line in block.splitlines():
 cells=[c.strip() for c in line.strip('|').split('|')]
 if not cells or cells[0] not in ['public','reference','to_asap7']:continue
 for m,val in zip(['cmi','anchor','affine','gp','mlp_adapt','cnp','residual','binary','full'],cells[2:]):assert abs(float(val)-lookup[cells[0],m,int(cells[1])])<0.000050001;count+=1
assert count==(2+5+5)*9
before=sha(P/'main.tex');subprocess.run(['python3',str(P/'render.py')],check=True);assert sha(P/'main.tex')==before
text=subprocess.check_output(['pdftotext',str(P/'main.pdf'),'-'],text=True)
for token in ['0.095980','0.088087','0.068084','7.643287','binary']:assert token in text,token
assert 'Overfull' not in (P/'main.log').read_text()
assert subprocess.check_output(['git','diff','--name-only','dce58bed002dd7440f963bcb21f28859bfcc6973'],cwd=ROOT,text=True).strip()==''
refs[str(source.relative_to(ROOT))]=sha(source);(P/'INPUT_SHA256.json').write_text(json.dumps(refs,indent=2))
(P/'INTEGRITY.json').write_text(json.dumps(dict(source_hashes_unchanged=True,E1_printed_entries_checked=count,rounding_check='printed four decimals within half last digit; source values unchanged',markdown_tex_deterministic=True,pdf_numeric_tokens_present=True,no_overfull_boxes=True,old_tracked_files_unchanged=True,body_sha256=sha(P/'DAC_REWRITE.md'),tex_sha256=sha(P/'main.tex'),pdf_sha256=sha(P/'main.pdf')),indent=2))
print('INTEGRITY_PASS',count)
