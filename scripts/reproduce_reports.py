"""Verify and export only the final paper's presented result data."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--sta',action='store_true')
p.add_argument('--output',type=Path,default=ROOT/'results/reproduced_final')
a=p.parse_args()
subprocess.run([sys.executable,str(ROOT/'scripts/verify_final_paper.py')],check=True)
a.output.mkdir(parents=True,exist_ok=False)
shutil.copytree(ROOT/'results/final_tables',a.output/'tables')
if a.sta:
 subprocess.run([sys.executable,str(ROOT/'scripts/plot_final_figure3.py'),'--output',str(a.output/'figure3')],check=True)
(a.output/'verification.json').write_text(json.dumps({'scope':'final manuscript only','tables':'CSV result data; headline/control aggregates verified','sta_redrawn':a.sta},indent=2)+'\n')
