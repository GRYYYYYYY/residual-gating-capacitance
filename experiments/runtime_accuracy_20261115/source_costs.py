"""Account supplied characterization and selected source stages separately."""
from common_runtime import *
def main():
    w=read(O/'WORKLOADS.json');ids={r['table_id'] for r in w['groups']['fem']}
    grid=read(R/'runs/reference_design_v2/grid.json');root=UP/'workspaces/pdkcap-v0/runs/reference_full_v2';support=[]
    for g in grid:
        if g['reference_id'] not in ids:continue
        for level in ['coarse','fine','wide']:
            p=root/(g['id']+'-'+level)/'result.json';v=read(p)
            support.append(dict(table_id=g['reference_id'],geometry_id=g['id'],level=level,result_sha256=sha(p),wall_s=v['wall_seconds'],cpu_s=v['cpu_seconds']))
    assert sum(r['level']=='fine' for r in support)==918
    paths=read(R/'experiments/dac_characterization_20261114/paths.json');models=read(R/'configs/paper_models.json');train=[]
    for setting in ['public','to_asap7']:
        choices=[('full',R/c['path']) for c in models[setting]['checkpoints']]
        choices += [(kind,Path(paths['control_root'])/'runs'/f'{setting}_{kind}_s{seed}'/'checkpoint.pt') for kind in ['binary','residual'] for seed in range(3)]
        base=R/'results/dac_characterization_20261114/learning';sel=read(base/f'{setting}_selection.json')
        choices += [(kind,base/f'{setting}_{kind}_lr{sel[kind]["lr"]:g}_s{seed}'/'checkpoint.pt') for kind in ['mlp','cnp'] for seed in range(3)]
        if setting=='to_asap7':
            base=R/'results/dac_characterization_20261114/attention';sel=read(base/'to_asap7_selection.json')
            choices += [('attentioncap',base/f'{setting}_lr{sel["lr"]:g}_s{seed}'/'checkpoint.pt') for seed in range(3)]
        for method,p in choices:
            receipt=p.parent/'COMPLETED.json';v=read(receipt)
            train.append(dict(setting=setting,method=method,checkpoint=str(p),checkpoint_sha256=v.get('checkpoint_sha256'),receipt_sha256=sha(receipt),steps=v.get('steps'),wall_seconds=v.get('wall_seconds'),cpu_seconds=v.get('cpu_seconds'),scope='selected final-stage receipt; initialization, source-label acquisition and hyperparameter selection costs are not fully aggregated'))
    write(O/'supplied_input_costs.json',dict(new_source_training_steps=0,target_support_geometries=918,target_support_fine_cpu_s=sum(r['cpu_s'] for r in support if r['level']=='fine'),target_support_three_level_cpu_s=sum(r['cpu_s'] for r in support),support_timer_scope='Existing result-file solver-internal timers; sum of worker CPU, not parallel elapsed. Supplied S is common to every method and is not charged per query.',public_rule_characterization_cost=None,public_cost_status='not measured; supplied native libraries',source_label_cost_complete=False,source_training_cost_complete=False,training_receipts=train,support_receipts=support,note='Nonzero supplied-input costs are separate from this continuation and from per-query latency. These selected receipts do not establish full lifecycle cost or speedup. No source training or S-label acquisition was rerun.'))
    print('supplied-cost receipts',len(support),len(train))
if __name__=='__main__':main()
