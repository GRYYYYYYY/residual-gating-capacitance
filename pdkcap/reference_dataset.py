"""Export verified full-grid matrices and role-defined labels without clipping."""
import argparse,collections,json
from pathlib import Path
import numpy as np
from .common import write_json,file_hash,digest


def components(matrix,metadata):
    c=np.asarray(matrix,float);i=metadata['target_index']
    if c.ndim!=2 or c.shape[0]!=c.shape[1] or not np.isfinite(c).all():raise ValueError('finite square matrix required')
    roles=[metadata['lateral_indices'],metadata['grounded_indices'],metadata['diagonal_indices']]
    members=[j for r in roles for j in r]
    if len(set(members))!=len(members) or set(members)!=(set(range(len(c)))-{i}):raise ValueError('electrode roles do not partition non-target conductors')
    result=np.array([-c[i,roles[0]].sum(),c[i].sum()-c[i,roles[1]].sum(),-c[i,roles[2]].sum()])
    if not np.isclose(result.sum(),c[i,i],rtol=1e-10,atol=1e-30):raise ValueError('target decomposition does not sum to self')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--design',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    summary=json.loads((a.run/'summary.json').read_text())
    if summary.get('phase')!='full' or not summary.get('all_requested_passed'):raise PermissionError('complete numerical grid not validated')
    grid_path=a.design/'grid.json'
    if file_hash(grid_path)!=summary['grid_sha256']:raise ValueError('grid identity differs')
    grid=json.loads(grid_path.read_text());contracts={c['reference_id']:c for c in json.loads((a.design/'contracts.json').read_text())}
    entries={json.loads(line)['id']:json.loads(line) for line in (a.run/'ledger.jsonl').read_text().splitlines()}
    groups=collections.defaultdict(list);matrices=[]
    for g in grid:
        levels={level:entries[g['id']+'-'+level] for level in ('coarse','fine','wide')}
        if any(e['status']!='completed' for e in levels.values()):raise ValueError('incomplete grid cell')
        metadata=g['spec']['metadata'];c=np.array(levels['fine']['result']['matrix_F_per_m'])
        label=components(c,metadata)
        uncertainty={level:np.abs(components(e['result']['matrix_F_per_m'],metadata)-label).tolist() for level,e in levels.items() if level!='fine'}
        groups[g['reference_id']].append((g,label,uncertainty))
        matrices.append(dict(id=g['id'],matrix_F_per_m=c.tolist(),role_metadata=metadata,component_uncertainty_F_per_m=uncertainty))
    a.output.mkdir(parents=True,exist_ok=False);tables=[]
    for ref,items in sorted(groups.items()):
        c=contracts[ref];m=items[0][0]['spec']['metadata'];rect=items[0][0]['spec']['rectangles_override'][0]
        material_er=next(r['er'] for r in c['materials'] if r['bottom']<=(rect[1]+rect[3])/2<r['top'])
        coordinates=[[g['spec']['metadata']['width_um'],g['spec']['metadata']['distance_um'],g['spec']['metadata']['lateral_spacing_um']] for g,y,u in items]
        tables.append(dict(table_id=ref,domain='ctf_derived_2d',process_id=c['process_id'],family=c['family'],partition=c['partition'],
            split_group=ref,coordinates=coordinates,labels=[y.tolist() for g,y,u in items],target_names=c['target_names'],units='F/m',
            materials=c['materials'],material_features=[rect[1],rect[3]-rect[1],material_er],metal=m['metal'],context_below=m['context_below'],context_above=m['context_above'],
            width_count=len({x[0] for x in coordinates}),reference_contract=c,
            component_uncertainty_F_per_m=[u for g,y,u in items]))
    with (a.output/'tables.jsonl').open('x') as f:
        for t in tables:f.write(json.dumps(t,allow_nan=False)+'\n')
    write_json(a.output/'matrices.json',matrices)
    write_json(a.output/'manifest.json',dict(source_summary_sha256=file_hash(a.run/'summary.json'),grid_sha256=file_hash(grid_path),
        contracts_sha256=file_hash(a.design/'contracts.json'),tables_sha256=file_hash(a.output/'tables.jsonl'),
        tables=len(tables),matrices=len(matrices),label_choice='fine',clipped=False,symmetrized=False))

if __name__=='__main__':main()
