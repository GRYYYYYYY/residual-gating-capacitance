import json,sys,platform,collections,subprocess
from pathlib import Path
from common import *
import torch,scipy
from pdkcap.active import fixed_population
D=ROOT/'docs/dac_characterization_20261114';R=ROOT/'results/dac_characterization_20261114'
torch.set_num_threads(1)
a=dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),reference='05d0717c31c3ebd38107c846cfa7712913078027',environment=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,scipy=scipy.__version__,cuda=torch.cuda.is_available()),files={},settings={},controls=[],numerical={})
for p in list((ROOT/'configs').glob('*.json'))+[ROOT/'database/catalog.json',ROOT/'database/packages.json',ROOT/'database/numerical_evidence.json']:
    a['files'][str(p.relative_to(ROOT))]=sha(p)
for s in MODELS:
    ms,sc=full(s);cs=controls(s,sc)
    cohorts={part:tables(s,part) for part in ('train','val','confirmation')}
    ids={p:{t['table_id'] for t in ts} for p,ts in cohorts.items()}
    assert not ids['train']&ids['val'];assert not ids['train']&ids['confirmation'];assert not ids['val']&ids['confirmation']
    a['settings'][s]={p:dict(count=len(ts),ids=sorted(ids[p]),processes=sorted({t['process_id'] for t in ts}),units=sorted({t['units'] for t in ts}),budget_coverage={str(b):sum(len(t['coordinates'])>=8 and len(fixed_population(t,11)[0])>=b for t in ts) for b in (4,8,16,32,64)},short_tables=sum(len(t['coordinates'])<8 for t in ts)) for p,ts in cohorts.items()}
    for c in MODELS[s]['checkpoints']:a['files'][c['path']]=sha(ROOT/c['path'])
    data=ROOT/source_config(s)['data'];a['files'][str(data.relative_to(ROOT))]=sha(data)
    data=ROOT/MODELS[s]['cohort'];a['files'][str(data.relative_to(ROOT))]=sha(data)
    for v in cs:
        for seed in range(3):
            d=Path(PATHS['control_root'])/'runs'/f'{s}_{v}_s{seed}'
            r=json.loads((d/'COMPLETED.json').read_text())
            a['controls'].append(dict(setting=s,variant=v,seed=seed,path=str(d/'checkpoint.pt'),sha256=sha(d/'checkpoint.pt'),steps=r['steps'],historical_wall_seconds=r['wall_seconds'],training_tables=r['training_tables'],loaded=True))
    if s=='public':
        ts=read_tables(data if False else ROOT/source_config(s)['data']);hold=[t for t in ts if t['partition']=='holdout']
        assert len(hold)==84
        assert not {t['table_id'] for t in hold}&(ids['train']|ids['val'])
        # Duplicate content must also be excluded.
        hh={tuple(t['curve_hashes']) for t in hold}
        assert not hh&{tuple(t['curve_hashes']) for t in cohorts['train']+cohorts['val']}
        a['holdout']=dict(count=len(hold),ids=[t['table_id'] for t in hold],train_val_content_overlap=0)
for gen in ('reference_full_v2','round2_full_v1','round3_full_v1'):
    p=Path(PATHS['solver_root'])/'runs'/gen/'summary.json';r=json.loads(p.read_text())
    a['numerical'][gen]=dict(path=str(p),sha256=sha(p),summary=r)
write(HERE/'MANIFEST.json',a)
print(json.dumps({s:{p:dict(count=v['count'],coverage=v['budget_coverage'],short=v['short_tables']) for p,v in x.items()} for s,x in a['settings'].items()},indent=2))
print('controls',len(a['controls']),'numerical',[(k,v['summary'].get('all_requested_passed')) for k,v in a['numerical'].items()])
