"""Label-sealed budget evaluation of the final model and matched controls.
Run from repository root after sourcing env.sh. Raw JSONL includes every Q/S,
component accumulator, prediction, failure and measured target-stage cost.
"""
import argparse, collections, copy, json, time, traceback, gzip
import numpy as np
import torch
from common import *
from pdkcap.active import fixed_population
from pdkcap.sampling import QueryOracle, geometry_order, select
from pdkcap.interpolation import predict,reduce_coordinates
from pdkcap.metrics import record,summarize
from pdkcap.round3_experts import gaussian_process, GP_CONFIGS
from unified.basis import anchor_only
from unified.cmi import multilinear
from unified.score import predict_table,dependency_group
sys.path.insert(0,str(ROOT/'experiments/paper_controls'))
from score_controls import affine_predict
PLAN=json.loads((HERE/'EXPERIMENT_PLAN.yaml').read_text())

def population(t,seed):
    n=len(t['coordinates'])
    if n>=8:return fixed_population(t,seed)
    if n<4:raise ValueError('ineligible n<4')
    q=np.sort(np.random.default_rng(seed).choice(n,max(1,round(.2*n)),replace=False))
    c=np.setdiff1d(np.arange(n),q);return c,q,np.array(geometry_order(t['coordinates'],c)[:2])
def trajectory(t,seed,strategy,budgets=None):
    g=public_input(t);x=np.asarray(g['coordinates']);c,q,initial=population(g,seed)
    bs=[b for b in (budgets or (PLAN['budgets'] if len(x)>=8 else [2])) if len(initial)<=b<=len(c)]
    oracle=QueryOracle(t['labels'],c,max(bs));history=[];sec=0.;snap=[]
    for i in initial:oracle.query(i);history.append(int(i))
    while True:
        o,v=oracle.observations
        if len(o) in bs:snap.append((o.copy(),v.copy(),sec,list(history)))
        if len(o)==max(bs):break
        start=time.perf_counter()
        interp=predict(x[o],v,x,'linear')[0] if strategy=='curvature' else None
        i=select(x,c,o,interpolation=interp,scales=np.maximum(np.sqrt(np.mean(v*v,axis=0)),1e-30),strategy=strategy,seed=seed+len(o)*997)
        sec+=time.perf_counter()-start
        oracle.query(i);history.append(int(i))
    return c,q,snap

class Predictors:
    def __init__(self,setting,selection=None,learned=True):
        torch.set_num_threads(1);self.setting=setting
        self.members,self.scales=full(setting)
        self.control=controls(setting,self.scales)
        self.selected=selection or {'gp':[1.,1e-6],'adapt_steps':50}
        self.learned=None
        if learned:
            from learning import Learned
            self.learned=Learned(setting)
    def __call__(self,name,t,o,v):
        # Callable interface accepts no truth, costs or hidden metadata.
        assert 'labels' not in t
        x=np.asarray(t['coordinates']);ys=np.asarray(self.scales['targets'][t['family']])
        if name=='full':p=predict_table(self.members,self.scales,t,o,v)[0]
        elif name=='pruned':p=predict_table(self.members,self.scales,t,o,v,basis=('linear',))[0]
        elif name in self.control:p=predict_table(self.control[name],self.scales,t,o,v,basis=('linear',))[0]
        elif name=='anchor':p=anchor_only(t,o,v,ys)[0]
        elif name=='cmi':
            a,b,axes=reduce_coordinates(x[o],x);floor=predict(x[o],v,x,'linear')[0]
            p=multilinear(a,v,b,len(axes),floor)[0] if axes else floor
        elif name=='affine':p=affine_predict(x[o],v,x,PLAN['affine'][self.setting])
        elif name=='gp':p=gaussian_process(x[o],v,x,*self.selected['gp'])
        elif name.startswith('gp_'):p=gaussian_process(x[o],v,x,*GP_CONFIGS[name])
        elif name=='pchip':p=predict(x[o],v,x,'pchip')[0] if len(np.unique(x[:,0]))==1 else predict(x[o],v,x,'linear')[0]
        elif self.learned is not None:p=self.learned.predict(name,t,o,v,self.selected.get('adapt_steps',50))
        else:raise ValueError(name)
        p=np.maximum(np.asarray(p),0);p[o]=v
        assert np.isfinite(p).all() and np.array_equal(p[o],v)
        return p

def costs(setting,ts):
    if setting=='public':return {}
    from pdkcap.round2_cost import cost_arrays
    root=Path(PATHS['solver_root'])
    return cost_arrays(ts,root/'runs/round3_design_v1',root/'runs/round3_full_v1')

def run_table(task):
    t,seed,strategy,methods=task;out=[]
    c,q,snaps=trajectory(t,seed,strategy);g=public_input(t);truth=np.asarray(t['labels'])
    for o,v,selection_s,history in snaps:
        meta=dict(setting=P.setting,data_seed=seed,strategy=strategy,budget=len(o),candidate_indices=c.tolist(),query_indices=q.tolist(),support_indices=o.tolist(),history=history,training_seed='ensemble_0_1_2',query_count=len(q),support_count=len(o),dependency_group=dependency_group(t),source_cost_known=False,selection_wall_seconds=selection_s)
        tc=COST.get(t['table_id'])
        meta.update(unique_reference_queries=len(o),solver_cpu_seconds_fine=None if tc is None else float(tc['fine'][o].sum()),solver_cpu_seconds_validated=None if tc is None else float(tc['certified'][o].sum()),solver_cost_kind='simulated_rule_access' if tc is None else 'recorded-cost replay',solver_wall_seconds=None)
        for m in methods:
            start=time.perf_counter();cpu=time.process_time()
            try:
                p=P(m,g,o,v)
                r=record(t,truth[q],p[q],**meta,method=m,status='ok',prediction=p.tolist(),p99_absolute=np.quantile(abs(p[q]-truth[q]),.99,axis=0).tolist())
                r['target_names']=t['target_names'];r['pchip_fallback']=m=='pchip' and len(np.unique(np.asarray(t['coordinates'])[:,0]))>1
            except Exception as e:r=dict(**meta,table_id=t['table_id'],method=m,status='failed',reason=repr(e),traceback=traceback.format_exc())
            r['prediction_and_adaptation_wall_seconds']=time.perf_counter()-start;r['prediction_and_adaptation_cpu_seconds']=time.process_time()-cpu
            out.append(r)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--setting',required=True);ap.add_argument('--split',default='confirmation',choices=['val','confirmation']);ap.add_argument('--out',required=True);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--pilot',action='store_true');ap.add_argument('--numerical-selection',action='store_true');a=ap.parse_args()
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=False)
    selection_file=HERE/f'selected_{a.setting}.json'
    selection=json.loads(selection_file.read_text()) if selection_file.exists() else None
    global P,COST
    P=Predictors(a.setting,selection,learned=not(a.pilot or a.numerical_selection))
    ts=tables(a.setting,a.split)
    if a.pilot:ts=ts[:1]
    COST={} if a.split=='val' else costs(a.setting,ts)
    methods=['cmi','anchor','affine','pchip','residual','binary','full','pruned']+list(GP_CONFIGS) if a.numerical_selection else (['cmi','anchor','affine','gp','pchip','residual','binary','full','pruned'] if a.pilot else PLAN['methods'])
    seeds=[11] if a.pilot or a.numerical_selection else PLAN['data_seeds']
    strategies=['farthest'] if a.pilot or a.numerical_selection or a.split=='val' else PLAN['strategies']
    tasks=[];ineligible=[]
    for t in ts:
        if len(t['coordinates'])<4:ineligible.append(t['table_id']);continue
        for seed in seeds:
            for strategy in strategies:tasks.append((t,seed,strategy,methods if strategy=='farthest' else PLAN['sampling_comparison_methods']))
    write(dest/'FROZEN.json',dict(run_id=dest.name,setting=a.setting,split=a.split,methods=methods,seeds=seeds,strategies=strategies,source_hashes={p.name:sha(p) for p in HERE.glob('*.py')},plan_sha256=sha(HERE/'EXPERIMENT_PLAN.yaml'),manifest_sha256=sha(HERE/'MANIFEST.json'),selection=selection,head=__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),workers=a.workers,ineligible=ineligible))
    start=time.perf_counter();rows=[]
    import multiprocessing as mp
    with gzip.open(dest/'records.jsonl.gz','xt') as f:
        def consume(iterator):
            for i,rs in enumerate(iterator):
                rows.extend(rs)
                for r in rs:f.write(json.dumps(r,allow_nan=False)+'\n')
                if i%25==0:
                    f.flush();print('completed tasks',i+1,'/',len(tasks),flush=True)
        if a.workers==1:
            consume(map(run_table,tasks))
        else:
            with mp.get_context('fork').Pool(a.workers) as pool:
                consume(pool.imap(run_table,tasks))
    write(dest/'COMPLETED.json',dict(records=len(rows),failed=sum(r['status']!='ok' for r in rows),tasks=len(tasks),elapsed_seconds=time.perf_counter()-start,records_sha256=sha(dest/'records.jsonl.gz')))
    print(dest,len(rows),'failed',sum(r['status']!='ok' for r in rows),'wall',time.perf_counter()-start,flush=True)
if __name__=='__main__':main()
