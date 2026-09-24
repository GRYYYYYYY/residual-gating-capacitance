"""New midpoint grids and explicitly supported boundary-layer 2D contexts."""
import argparse
import copy
import json
from pathlib import Path
import numpy as np
from .common import ROOT, FAMILIES, file_hash, write_json
from .reference import parse_ctf


def geometry(stack, index, family, width, distance, extent_factor=2.):
    metals = stack['metals']
    if not 0 <= index < len(metals) or family not in FAMILIES:
        raise ValueError('invalid layer or family')
    layer = metals[index]
    if layer['name'] == 'OD':
        raise ValueError('OD is not an ordinary interconnect reference')
    needs_below = family in ('OVER', 'OVERUNDER')
    needs_above = family in ('UNDER', 'OVERUNDER', 'DIAGUNDER')
    if needs_below and index == 0 or needs_above and index == len(metals)-1:
        raise ValueError('required context electrode does not exist')
    if width <= 0 or distance <= 0 or extent_factor < 1:
        raise ValueError('invalid dimensions or domain factor')
    z0, z1 = layer['bottom'], layer['top']
    spacing = layer['smin'] if family == 'DIAGUNDER' else distance
    rects = [[-width/2, z0, width/2, z1]]
    for sign in (-1, 1):
        cx = sign*(width+spacing)
        rects.append([cx-width/2, z0, cx+width/2, z1])
    grounded, diagonal = [], []
    halfplane = 32*layer['wmin']+16*layer['smin']
    contexts = ([metals[index-1]] if needs_below else [])
    if family in ('UNDER', 'OVERUNDER'):
        contexts.append(metals[index+1])
    for other in contexts:
        grounded.append(len(rects))
        rects.append([-halfplane, other['bottom'], halfplane, other['top']])
    if family == 'DIAGUNDER':
        above = metals[index+1]
        diagonal.append(len(rects)); cx = width+distance
        rects.append([cx-width/2, above['bottom'], cx+width/2, above['top']])
    extent = max(4., 2*stack['plates'][-1][0], 2*halfplane)*extent_factor
    return dict(kind='wire', h=min(layer['thickness'], width, spacing)/3,
        extent=extent, width=width, gaps=[spacing, spacing], rectangles_override=rects,
        materials=copy.deepcopy(stack['plates'])+[[extent, 1.]], corner_refinement=True,
        far_field_size=extent/10, far_field_distance=extent/4,
        refine_conductor_indices=[0, 1, 2]+diagonal,
        metadata=dict(family=family, target_index=0, lateral_indices=[1, 2],
            grounded_indices=grounded, diagonal_indices=diagonal,
            width_um=width, distance_um=distance, lateral_spacing_um=spacing,
            context_plane_halfwidth_um=halfplane, master_layer=layer['name'],
            metal=index+1, context_below=index if needs_below else 0,
            context_above=index+2 if needs_above else 0))


def build():
    protocol = json.loads((ROOT/'configs/round3_protocol.json').read_text())
    original = json.loads((ROOT/'runs/reference_design_v2/contracts.json').read_text())
    contracts, grid = [], []
    for process in ('asap7', 'freepdk15'):
        template = next(c for c in original if c['process_id'] == process)
        stack = parse_ctf(template['source_ctf'])
        if stack['sha256'] != template['source_sha256']:
            raise ValueError('CTF source drift')
        cfg = protocol['reference'][process]
        contexts = [(name, FAMILIES, 'val', 'new_geometry') for name in cfg['validation']]
        contexts += [(name, FAMILIES, 'confirmation', 'new_geometry') for name in cfg['confirmation']]
        contexts += [(name, families, 'confirmation', 'boundary_layer') for name, families in cfg['boundary'].items()]
        for name, families, partition, cohort in contexts:
            index = next(i for i, layer in enumerate(stack['metals']) if layer['name'] == name)
            layer = stack['metals'][index]
            old_w = np.linspace(layer['wmin'], 4*layer['wmin'], 9)
            old_s = np.geomspace(layer['smin'], 16*layer['smin'], 17)
            widths = (old_w[:-1]+old_w[1:])/2
            distances = np.sqrt(old_s[:-1]*old_s[1:])
            for family in families:
                cid = f'r3-{process}-{name}-{family}'
                c = copy.deepcopy(next(c for c in original if c['process_id'] == process and c['family'] == family))
                c.update(reference_id=cid, partition=partition, layer_index=index,
                    layer_context_index=index, confirmation_cohort=cohort,
                    dependency_group=f'{process}-{name}', numerical_outer_extent_factor=protocol['reference']['extent_factor'])
                contracts.append(c)
                for wi, width in enumerate(widths):
                    for si, distance in enumerate(distances):
                        spec = geometry(stack, index, family, float(width), float(distance), protocol['reference']['extent_factor'])
                        grid.append(dict(id=f'{cid}-w{wi:02d}-s{si:02d}', reference_id=cid, wi=wi, si=si, spec=spec))
    if len(contracts) != 27 or len(grid) != 3456:
        raise ValueError('reference population differs from protocol')
    return contracts, grid


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); contracts, grid = build()
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output/'contracts.json', contracts); write_json(args.output/'grid.json', grid)
    profile = [g for g in grid if g['wi'] == 0 and g['si'] == 0]
    write_json(args.output/'profile_grid.json', profile)
    write_json(args.output/'manifest.json', dict(tables=len(contracts), matrices=len(grid),
        calls=3*len(grid), profile_calls=3*len(profile), source_sha256=file_hash(__file__),
        grid_sha256=file_hash(args.output/'grid.json'),
        protocol_sha256=file_hash(ROOT/'configs/round3_protocol.json'),
        scope='new geometries and separately reported boundary layers; same two stacks'))


if __name__ == '__main__': main()
