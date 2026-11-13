import copy,time
from evaluate import *
out=[]
for setting in MODELS:
    p=Predictors(setting,learned=False);t=tables(setting,'val')[0];c,q,snaps=trajectory(t,11,'farthest');o,v,_,_=snaps[0]
    g=public_input(t);start=time.perf_counter()
    got=p('full',g,o,v);expected=predict_table(p.members,p.scales,t,o,v)[0]
    assert np.array_equal(got,expected)
    poisoned=copy.deepcopy(t);y=np.asarray(t['labels']);hidden=np.setdiff1d(np.arange(len(y)),o);poison=np.array(y);poison[hidden]=np.arange(len(hidden))[:,None]+1e20;poisoned['labels']=poison.tolist()
    for m in ('full','pruned','residual','binary','cmi','anchor','affine','gp','pchip'):
        assert np.array_equal(p(m,g,o,v),p(m,public_input(poisoned),o,v))
    for strategy in ('farthest','random','curvature'):
        # After initial support, compare the NEXT choice only: future queries
        # legitimately expose changed labels, and may alter later choices.
        interp=predict(np.asarray(g['coordinates'])[o],v,g['coordinates'],'linear')[0]
        a=select(g['coordinates'],c,o,interpolation=interp,scales=np.maximum(abs(v).mean(0),1e-30),strategy=strategy,seed=11)
        b=select(public_input(poisoned)['coordinates'],c,o,interpolation=interp,scales=np.maximum(abs(v).mean(0),1e-30),strategy=strategy,seed=11)
        assert a==b
    oracle=QueryOracle(t['labels'],c,len(o))
    for i in o:oracle.query(i);oracle.query(i)
    assert len(oracle.observations[0])==len(o)
    try:oracle.query(q[0]);raise AssertionError('sealed query accepted')
    except PermissionError:pass
    try:oracle.query(next(i for i in c if i not in o));raise AssertionError('overbudget accepted')
    except RuntimeError:pass
    out.append(dict(setting=setting,adapter_bit_exact=True,hidden_label_poisoning=True,selection_invariant=True,observations_exact=True,initial_charged=True,components_charged_once=True,query_rejected=True,cache_hit_free=True,seconds=time.perf_counter()-start))
write(ROOT/'results/dac_characterization_20261114/boundary_checks.json',out)
print(json.dumps(out,indent=2))
