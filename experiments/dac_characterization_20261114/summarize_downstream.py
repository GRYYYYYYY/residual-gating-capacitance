import csv,json,re,collections
from common import *
from scipy.stats import spearmanr
R=ROOT/'results/dac_characterization_20261114/downstream'
OUT=ROOT/'results/dac_characterization_20261114/summary';OUT.mkdir(exist_ok=True)
def readtsv(p):
    with p.open() as f:return list(csv.DictReader(f,delimiter='\t'))
def writecsv(name,rows):
    if not rows:
        # A final empty failure list must replace any interim missing-case list.
        (OUT/name).write_text('case,variant,status\n')
        return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w') as f:w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)
rows=[];fail=[];provenance=[]
for case in json.loads((ROOT/'database/sta_cases.json').read_text()):
    d=R/'native'/case;gold=d/'golden'
    if not (gold/'COMPLETED.json').exists():fail.append(dict(case=case,status='missing golden'));continue
    golden=json.loads((gold/'COMPLETED.json').read_text());assert golden['status']=='ok'
    archived=json.loads((ROOT/'database/sta_cases.json').read_text())[case]['variants']['golden']
    for key,oldkey,tol in [('worst_slack_native','worst_slack_native',1e-5),('tns_native','tns_native',.01)]:
        assert abs(golden[key]-archived[oldkey])<=max(tol,abs(archived[oldkey])*1e-6),(case,key,golden[key],archived[oldkey])
    log=(gold/'native.log').read_text();unit=re.search(r' time 1(\w+)',log)[1];scale={'ps':.001,'ns':1.,'us':1000.}[unit]
    ep={r['endpoint']:float(r['slack'])*scale for r in readtsv(gold/'endpoints.tsv')};eps=sorted(ep);a=np.array([ep[k] for k in eps]);order=np.argsort(a,kind='stable');viol=a<0
    gp=json.loads((gold/'FROZEN.json').read_text())['provenance'];paths={r['endpoint']:r for r in readtsv(gold/'paths.tsv')}
    for p in sorted(d.glob('*/COMPLETED.json')):
        if p.parent==gold:continue
        state=json.loads(p.read_text());name=p.parent.name
        if state['status']!='ok':fail.append(dict(case=case,variant=name,**state));continue
        prov=json.loads((p.parent/'FROZEN.json').read_text())['provenance']
        assert all(prov[k]==gp[k] for k in ('odb','sdc','openroad','libs','tcl'))
        bmap={r['endpoint']:float(r['slack'])*scale for r in readtsv(p.parent/'endpoints.tsv')};assert set(bmap)==set(ep)
        b=np.array([bmap[k] for k in eps]);assert np.array_equal(np.isfinite(a),np.isfinite(b));finite=np.isfinite(a)&np.isfinite(b);err=abs(b[finite]-a[finite]);v=b<0
        method,budget,seed=re.fullmatch(r'(.+)_B(\d+)_s(\d+)',name).groups();caps=state['comparison']['metrics']['capacitance']
        r=dict(case=case,method=method,budget=int(budget),data_seed=int(seed),net_cap_nrmse=caps['nrmse'],net_cap_mae_native=caps['mae'],net_cap_rmse_native=caps['rmse'],cap_unit=json.dumps(state['comparison']['units']['*C_UNIT']),slack_mae_ns=float(err.mean()),slack_p95_ns=float(np.quantile(err,.95)),slack_p99_ns=float(np.quantile(err,.99)),slack_max_abs_ns=float(err.max()),ws_abs_ns=abs(state['worst_slack_native']-golden['worst_slack_native'])*scale,tns_abs_ns=abs(state['tns_native']-golden['tns_native'])*scale,endpoints=len(eps),finite_endpoints=int(finite.sum()),false_negative=int((viol&~v).sum()),false_positive=int((~viol&v).sum()),spearman=float(spearmanr(a[finite],b[finite]).statistic),extraction_seconds=state['extraction_seconds'],native_wall_seconds=state['wall_seconds'])
        paths_b={r['endpoint']:r for r in readtsv(p.parent/'paths.tsv')};assert set(paths_b)==set(paths);bo=np.argsort(b,kind='stable')
        for k in (10,20,50,100):
            aa={eps[i] for i in order[:k]};bb={eps[i] for i in bo[:k]};r[f'endpoint_overlap_at{k}']=len(aa&bb)/min(k,len(eps))
            pa={(e,paths[e]['startpoint'],paths[e]['pins']) for e in aa if e in paths};pb={(e,paths_b[e]['startpoint'],paths_b[e]['pins']) for e in bb if e in paths_b};r[f'full_path_overlap_at{k}']=len(pa&pb)/max(1,len(pa))
        rows.append(r);provenance.append(dict(case=case,variant=name,**prov))
writecsv('downstream_raw.csv',rows);writecsv('downstream_failures.csv',fail)
expected=8*2*3*5
with (OUT/'downstream_status.json').open('w') as f:json.dump(dict(completed=len(rows),expected=expected,failures=fail,complete=len(rows)==expected and not fail),f,indent=2)
with (OUT/'downstream_provenance.json').open('w') as f:json.dump(provenance,f,indent=2)
groups=collections.defaultdict(list)
for r in rows:groups[r['case'],r['method'],r['budget']].append(r)
means=[]
for (case,m,b),rs in groups.items():
    means.append(dict(case=case,method=m,budget=b,seeds=len(rs),**{k:float(np.mean([r[k] for r in rs])) for k in ('net_cap_nrmse','slack_mae_ns','slack_p95_ns','slack_p99_ns','ws_abs_ns','tns_abs_ns','false_negative','false_positive','extraction_seconds')}))
writecsv('downstream_means.csv',means)
print('native completed',len(rows),'expected',expected,'failures',len(fail),flush=True)
