"""Presentation-only correction: shorter unclipped axis label; CSVs unchanged."""
import json,shutil,subprocess
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from paths import *
p=ROOT/'paper/dac_mechanism_resume_20261114';old=OUT/'presentation_original';old.mkdir(exist_ok=False)
for n in ['paired_effects.pdf','paired_effects.png']:shutil.copyfile(OUT/n,old/n)
shutil.copyfile(p/'main.pdf',old/'main.pdf');shutil.copyfile(OUT/'PAPER_SUCCESS.json',old/'PAPER_SUCCESS.json')
e=pd.read_csv(OUT/'EFFECTS_BY_SEED.csv');s=pd.read_csv(OUT/'EFFECT_SUMMARY.csv');metrics=['C_Full','C_binary','D_Full','D_binary','I','G'];x=np.arange(6)
fig,ax=plt.subplots(figsize=(6.8,4.3))
for seed in range(3):ax.scatter(x+(seed-1)*.12,[e[e.train_seed==seed][m].iloc[0] for m in metrics],label=f'train seed {seed}',s=32)
s=s.set_index('effect').loc[metrics];mean=s['mean'].values;ax.errorbar(x,mean,yerr=[mean-s.conditional_group_ci_low.values,s.conditional_group_ci_high.values-mean],fmt='k_',capsize=4,label='mean; paired group 95% interval');ax.axhline(0,color='gray',lw=.8);ax.set_xticks(x,['C Full','C binary','D Full','D binary','I','G']);ax.set_ylabel('Paired NRMSE difference');ax.legend(fontsize=7);fig.tight_layout();fig.savefig(OUT/'paired_effects.pdf');fig.savefig(OUT/'paired_effects.png',dpi=180);plt.close(fig)
shutil.copyfile(OUT/'paired_effects.pdf',p/'figures/paired_effects.pdf')
for i in range(2):
 with (p/f'presentation_compile{i+1}.txt').open('w') as f:subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=p,stdout=f,stderr=subprocess.STDOUT,check=True)
r=json.loads((OUT/'PAPER_SUCCESS.json').read_text());assert sha(p/'main.tex')==r['tex_sha256'] and sha(p/'DAC_REWRITE.md')==r['markdown_sha256'];r.update(pdf_sha256=sha(p/'main.pdf'),presentation_change='shorten clipped effect-axis label; numerical data and main text unchanged',original_paper_receipt_sha256=sha(OUT/'PAPER_SUCCESS.json'),presentation_source_sha256=sha(Path(__file__)))
atomic_json(OUT/'PAPER_FINAL_SUCCESS.json',r)
with (DOC/'FINAL_DECISION.md').open('a') as f:f.write('\nThe aggregate local Full-L advantage must not be read as a B4 advantage: G(B4) is negative in all three seeds. Full D is negative in one seed; I is negative in all three. Low-support training worsens Full at B16/B32 and binary at B32, relative to matched H. The original-support checks also expose retention costs. This does not establish a Full-specific mismatch remedy or justify continuing Full expansion. End this bounded study.\n')
with (DOC/'REPRODUCE.md').open('a') as f:f.write('\nPresentation-only finalization: presentation.py regenerates the paired-effect chart from the same CSVs with a shorter unclipped axis label and recompiles the unchanged TeX. Original plot/PDF and receipt remain under presentation_original; PAPER_FINAL_SUCCESS binds the final PDF. This changes no numerical values, metrics or parameters.\n')
print('PRESENTATION_FINALIZED',flush=True)
