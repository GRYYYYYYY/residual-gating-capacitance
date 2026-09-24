"""Sequential CPU model study with validation-only eta selection and frozen sources."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from .common import ROOT,file_hash,write_json
from .budget import authorization


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    authorization('training');a.output.mkdir(parents=True,exist_ok=False)
    snapshot=a.output/'source_snapshot';snapshot.mkdir()
    files=sorted((ROOT/'pdkcap').glob('*.py'));hashes={str(f):file_hash(f) for f in files}
    for f in files:shutil.copyfile(f,snapshot/f.name)
    write_json(a.output/'manifest.json',dict(data_sha256=file_hash(a.data),protocol_sha256=file_hash(ROOT/'configs/protocol.json'),source_hashes=hashes,
        selection='seed 0 final-step validation NRMSE, average of mcar/block/extrapolation at 30%; tie smaller eta',steps=2000))
    runs={}
    def train(variant,eta,seed):
        key=f'{variant}_eta{eta:g}_seed{seed}';out=a.output/key
        if key in runs:return runs[key]
        for name,expected in hashes.items():
            if file_hash(name)!=expected:raise RuntimeError('source changed during formal study')
        cmd=[sys.executable,'-m','pdkcap.train','--data',str(a.data),'--output',str(out),'--steps','2000','--seed',str(seed),'--variant',variant,'--eta',str(eta),'--purpose','formal']
        with (a.output/f'{key}.log').open('x') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
        result=json.loads((out/'result.json').read_text());runs[key]=dict(path=str(out.resolve()),result=result)
        print(key,result['validation_nrmse'],flush=True)
        return runs[key]
    train('direct',0.,0)
    scores=[]
    for eta in (0.,.01,.05):
        result=train('residual',eta,0)
        scores.append(dict(eta=eta,score=float(np.mean(list(result['result']['validation_nrmse'].values())))))
    selected=min(scores,key=lambda r:(r['score'],r['eta']))['eta']
    write_json(a.output/'selection.json',dict(eta=selected,candidates=scores,selection_partition='val',test_labels_accessed=False))
    for seed in (1,2):
        train('direct',0.,seed);train('residual',0.,seed);train('residual',selected,seed)
    checkpoints={}
    for method,variant,eta in [('direct','direct',0.),('residual','residual',0.),('residual_group_dro','residual',selected)]:
        checkpoints[method]=[str(Path(runs[f'{variant}_eta{eta:g}_seed{seed}']['path'])/'checkpoint.pt') for seed in (0,1,2)]
    write_json(a.output/'completed.json',dict(status='completed',selected_eta=selected,checkpoints=checkpoints,
        fit_count=len(runs),test_labels_accessed=False,source_hashes=hashes,
        training_wall_seconds=sum(v['result']['wall_seconds'] for v in runs.values())))

if __name__=='__main__':main()
