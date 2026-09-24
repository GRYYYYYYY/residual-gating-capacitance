"""New explicitly declared CTF-derived 2D references, not original author labels."""
import argparse,copy,json,re
from pathlib import Path
import numpy as np
from .common import ROOT,FAMILIES,file_hash,digest,write_json


def parse_ctf(path):
    # Resolve independently downloaded inputs from the original basename.
    path = Path(path)
    if not path.is_file():
        import os
        path = Path(os.environ.get('RG_CTF_ROOT', ROOT / 'upstream/ctf')) / path.name
    cursor=0.;metals=[];plates=[];regions=[]
    for kind,name,body in re.findall(r'(dielectric|conductor)\s+(\S+)\s*\{([^}]+)\}',Path(path).read_text()):
        fields={k:float(v) for k,v in re.findall(r'^\s*(\w+)\s+([-+\d.eE]+)\s*$',body,re.M)}
        h=fields['thickness']
        if h<=0:raise ValueError('nonpositive thickness')
        if kind=='dielectric':
            er=fields['er'];upper=round(cursor+h,12)
            if er<=0:raise ValueError('nonpositive permittivity')
            regions.append(dict(name=name,bottom=cursor,top=upper,er=er))
            if plates and plates[-1][1]==er:plates[-1][0]=upper
            else:plates.append([upper,er])
            cursor=upper
        else:
            metals.append(dict(name=name,bottom=cursor,top=round(cursor+h,12),**fields))
    if not metals or not plates:raise ValueError('empty CTF stack')
    return dict(source=str(Path(path).resolve()),sha256=file_hash(path),metals=metals,plates=plates,regions=regions)


def geometry(stack,index,family,width,distance):
    metals=stack['metals'];layer=metals[index];below=metals[index-1];above=metals[index+1]
    z0,z1=layer['bottom'],layer['top'];spacing=layer['smin'] if family=='DIAGUNDER' else distance
    rects=[[-width/2,z0,width/2,z1]]
    for sign in (-1,1):
        cx=sign*(width+spacing);rects.append([cx-width/2,z0,cx+width/2,z1])
    grounded=[];diagonal=[]
    # Plane footprint fixed across all widths/distances in a context (not query-dependent).
    halfplane=32*layer['wmin']+16*layer['smin']
    for other in ([below] if family=='OVER' else [above] if family=='UNDER' else [below,above] if family=='OVERUNDER' else []):
        grounded.append(len(rects));rects.append([-halfplane,other['bottom'],halfplane,other['top']])
    if family=='DIAGUNDER':
        diagonal.append(len(rects));cx=width+distance
        rects.append([cx-width/2,above['bottom'],cx+width/2,above['top']])
    extent=max(4.,2*stack['plates'][-1][0],2*halfplane)
    plates=copy.deepcopy(stack['plates'])+[[extent,1.]]
    h=min(layer['thickness'],width,spacing)/3
    return dict(kind='wire',h=h,extent=extent,width=width,gaps=[spacing,spacing],
                rectangles_override=rects,materials=plates,corner_refinement=True,
                far_field_size=extent/10,far_field_distance=extent/4,
                metadata=dict(family=family,target_index=0,lateral_indices=[1,2],
                    grounded_indices=grounded,diagonal_indices=diagonal,
                    width_um=width,distance_um=distance,lateral_spacing_um=spacing,
                    context_plane_halfwidth_um=halfplane,master_layer=layer['name'],
                    metal=index+1,context_below=index if family in ('OVER','OVERUNDER') else 0,
                    context_above=index+2 if family!='OVER' else 0))


def build(root):
    contracts=[];pilot=[];grids=[]
    for technology in ('asap7','freepdk15'):
        stack=parse_ctf(root/f'{technology}.ctf')
        candidates=[i for i,m in enumerate(stack['metals']) if i>0 and i<len(stack['metals'])-1 and m['name']!='OD'][:4]
        if len(candidates)!=4:raise ValueError('four interior layer contexts required')
        for ci,index in enumerate(candidates):
            layer=stack['metals'][index]
            for family in FAMILIES:
                cid=f'{technology}-{layer["name"]}-{family}'
                widths=np.linspace(layer['wmin'],4*layer['wmin'],9)
                distances=np.geomspace(layer['smin'],16*layer['smin'],17)
                contract=dict(reference_id=cid,process_id=technology,family=family,source_ctf=stack['source'],source_sha256=stack['sha256'],
                    dimension=2,input_units='um',output_units='F/m',partition='train' if ci<2 else 'val' if ci==2 else 'test',
                    target_names=['lateral_coupling','ground_cap','diagonal_coupling'],
                    original_label_equivalence=False,commercial_pdk_equivalence=False,
                    declarations=['CTF dielectric records advance height; conductor records do not.',
                        'Infinite extrusion; isotropic horizontal materials extended laterally.',
                        'All exterior edges grounded; z=0 is a declared infinite ground plane.',
                        'Air er=1 above final CTF dielectric; no absent wires or devices inferred.',
                        'Finite context planes are separate electrodes held at zero for target excitation.',
                        'Ground label includes exterior shield and explicit grounded context electrodes.',
                        'Lateral label sums both side-wire couplings; diagonal is a separate target.',
                        'DIAGUNDER distance is off-layer edge offset; lateral gap stays at source smin.'],
                    layer_context_index=ci,layer_index=index,materials=stack['regions'])
                contracts.append(contract)
                for wi,w in enumerate(widths):
                    for si,s in enumerate(distances):
                        spec=geometry(stack,index,family,float(w),float(s))
                        grids.append(dict(id=f'{cid}-w{wi:02d}-s{si:02d}',reference_id=cid,wi=wi,si=si,spec=spec))
                # Eight center fixtures, one per stack/family; pilot does not read validation/test labels.
                if ci==0:
                    spec=geometry(stack,index,family,float(widths[4]),float(distances[8]))
                    for name,hfactor,efactor in [('coarse',1.,1.),('fine',.5,1.),('wide',.5,2.)]:
                        spec2=copy.deepcopy(spec);spec2['h']*=hfactor;spec2['extent']*=efactor
                        spec2['materials'][-1][0]=spec2['extent']
                        pilot.append(dict(id=f'{cid}-{name}',reference_id=cid,level=name,spec=spec2))
    for name,h in [('coarse',.12),('fine',.06)]:
        pilot.append(dict(id=f'analytic-coax-{name}',reference_id='analytic-coax',level=name,
                          spec=dict(kind='coax',h=h,er_inner=2.,er_outer=1.)))
    return contracts,grids,pilot


def main():
    p=argparse.ArgumentParser();p.add_argument('--ctf-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);contracts,grids,pilot=build(a.ctf_root)
    write_json(a.output/'contracts.json',contracts);write_json(a.output/'grid.json',grids);write_json(a.output/'pilot.json',pilot)
    write_json(a.output/'summary.json',dict(contexts=len(contracts),unique_grid_matrices=len(grids),pilot_solves=len(pilot),
        width_count=9,distance_count=17,full_three_level_solves=3*len(grids),
        status='specified_not_solved',contract_hash=digest(contracts)))
    print(json.dumps(dict(contexts=len(contracts),grid=len(grids),pilot=len(pilot))))

if __name__=='__main__':main()
