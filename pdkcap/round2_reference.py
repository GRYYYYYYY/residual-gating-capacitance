"""Prospective layers of the existing declared 2D problem; no label access."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
from .common import ROOT, FAMILIES, file_hash, write_json
from .reference import geometry, parse_ctf


def build(extent_factor=1.):
    if extent_factor<1:raise ValueError('boundary may only be expanded')
    protocol = json.loads((ROOT/'configs/round2_protocol.json').read_text())
    original = json.loads((ROOT/'runs/reference_design_v2/contracts.json').read_text())
    contracts, grid = [], []
    for process in ('asap7', 'freepdk15'):
        template = next(c for c in original if c['process_id'] == process)
        stack = parse_ctf(template['source_ctf'])
        if stack['sha256'] != template['source_sha256']:
            raise ValueError('upstream CTF drift')
        layers = protocol['reference'][process]
        for ci, name in enumerate(layers['validation'] + layers['confirmation']):
            index = next(i for i, m in enumerate(stack['metals']) if m['name'] == name)
            if any(c['process_id'] == process and c['layer_index'] == index for c in original):
                raise ValueError('prospective layer already used')
            layer = stack['metals'][index]
            for family in FAMILIES:
                cid = f'{process}-{name}-{family}'
                c = copy.deepcopy(next(c for c in original if c['process_id']==process and c['family']==family))
                c.update(reference_id=cid, partition='val' if ci==0 else 'confirmation',
                         layer_context_index=4+ci, layer_index=index,
                         confirmation_cohort='prospective-layer-round2',
                         dependency_group=f'{process}-{name}')
                contracts.append(c)
                for wi, width in enumerate(np.linspace(layer['wmin'], 4*layer['wmin'], 9)):
                    for si, distance in enumerate(np.geomspace(layer['smin'], 16*layer['smin'], 17)):
                        spec = geometry(stack,index,family,float(width),float(distance))
                        spec['extent']*=extent_factor
                        spec['materials'][-1][0]=spec['extent']
                        spec['far_field_size']=spec['extent']/10
                        spec['far_field_distance']=spec['extent']/4
                        spec['refine_conductor_indices'] = [0,1,2] + spec['metadata']['diagonal_indices']
                        grid.append(dict(id=f'{cid}-w{wi:02d}-s{si:02d}',reference_id=cid,wi=wi,si=si,spec=spec))
    return contracts, grid


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--extent-factor',type=float,default=1.);a=p.parse_args()
    contracts,grid=build(a.extent_factor);a.output.mkdir(parents=True,exist_ok=False)
    for c in contracts:c['numerical_outer_extent_factor']=a.extent_factor
    write_json(a.output/'contracts.json',contracts);write_json(a.output/'grid.json',grid)
    # One training-independent numerical fixture per new process/layer/family,
    # at the demanding minimum width/spacing; no method scoring.
    profile=[g for g in grid if g['wi']==0 and g['si']==0]
    write_json(a.output/'profile_grid.json',profile)
    write_json(a.output/'manifest.json',dict(tables=len(contracts),matrices=len(grid),solves=3*len(grid),
        protocol_sha256=file_hash(ROOT/'configs/round2_protocol.json'),extent_factor=a.extent_factor,
        grid_sha256=file_hash(a.output/'grid.json'),source_sha256=file_hash(__file__),
        scope='new layers, same two materials and declared 2D physics; not new technologies'))

if __name__=='__main__':main()
