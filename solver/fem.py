"""Conforming 2-D dielectric FEM. Coordinates in um, capacitance per length F/m.

Two-dimensional stiffness is length-scale invariant: both derivatives and
area transform, so using um coordinates does not introduce a 1e6 factor.
All non-driven conductor boundaries and the explicit outer shield are grounded.
Reference labels are never clipped or symmetrized.
"""
from pathlib import Path
import math
import numpy as np
import gmsh
from scipy.sparse.linalg import splu
from skfem import MeshTri, Basis, FacetBasis, ElementTriP2, BilinearForm, Functional, asm
from skfem.helpers import dot, grad

EPS0 = 8.8541878128e-12


def _start():
    gmsh.initialize()
    gmsh.option.setNumber('General.Terminal', 0)
    gmsh.option.setNumber('General.NumThreads', 1)
    gmsh.option.setNumber('Mesh.MshFileVersion', 2.2)
    gmsh.model.add('electrostatic')


def _group(dim, entities, name):
    if not entities:
        raise ValueError(f'empty physical group {name}')
    tag = gmsh.model.addPhysicalGroup(dim, entities)
    gmsh.model.setPhysicalName(dim, tag, name)


def coax_mesh(path, h, er_inner=2.0, er_outer=1.0):
    if h <= 0 or min(er_inner, er_outer) <= 0:
        raise ValueError('positive dimensions/materials required')
    _start()
    try:
        geo = gmsh.model.geo
        center = geo.addPoint(0, 0, 0, h)
        loops, arcs_all = [], []
        for radius in (1., 1.5, 2.):
            pts = [geo.addPoint(radius * math.cos(i*math.pi/2), radius * math.sin(i*math.pi/2), 0, h) for i in range(4)]
            arcs = [geo.addCircleArc(pts[i], center, pts[(i+1)%4]) for i in range(4)]
            loops.append(geo.addCurveLoop(arcs)); arcs_all.append(arcs)
        surfaces = [geo.addPlaneSurface([loops[i+1], loops[i]]) for i in range(2)]
        geo.synchronize()
        _group(2, [surfaces[0]], 'eps_inner'); _group(2, [surfaces[1]], 'eps_outer')
        _group(1, arcs_all[0], 'c0'); _group(1, arcs_all[2], 'ground')
        gmsh.model.mesh.generate(2)
        gmsh.write(str(path))
    finally:
        gmsh.finalize()
    return {'eps_inner': er_inner, 'eps_outer': er_outer}, ['c0']


def validate_dielectric_patches(patches, extent):
    result = []
    for patch in patches:
        if len(patch) != 5 or not all(math.isfinite(x) for x in patch):
            raise ValueError('finite [x0,z0,x1,z1,er] patch required')
        a,b,c,d,er = patch
        if not (-extent <= a < c <= extent and 0 <= b < d <= extent and er > 0):
            raise ValueError('invalid dielectric patch dimensions/permittivity')
        for x,y,xx,yy,_ in result:
            if min(c,xx) > max(a,x) and min(d,yy) > max(b,y):
                raise ValueError('overlapping dielectric patches need an explicit disjoint partition')
        result.append(tuple(patch))
    return result


def wire_mesh(path, h, extent=12., reflected=False, metal_z=(1., 1.4),
              width=0.4, gaps=(0.5, 0.8), materials=None, corner_refinement=False,
              rectangles_override=None, far_field_size=None, far_field_distance=None,
              dielectric_patches=None, refine_conductor_indices=None):
    """Three parallel wires in layered dielectric with explicit outer shield.

    Materials are ordered (z_top, relative_epsilon) ending at extent. This
    fixture is a declared idealized cross section, not a full PDK extraction.
    Optional disjoint dielectric_patches are [x0,z0,x1,z1,er] rectangles
    overriding the horizontal background outside conductors. No PDK layer is
    automatically approximated by a patch; callers declare and validate it.
    """
    materials = materials or [(3., 3.9), (4., 6.5), (extent, 1.)]
    if min(h, width, *gaps) <= 0 or not 0 < metal_z[0] < metal_z[1] < extent:
        raise ValueError('invalid geometry')
    tops = [z for z, er in materials]
    if any(er <= 0 for z, er in materials) or any(a >= b for a,b in zip([0.]+tops[:-1], tops)) or tops[-1] != extent:
        raise ValueError('invalid material partition')
    centers = [0., -width-gaps[0], width+gaps[1]]
    if reflected: centers = [-x for x in centers]
    rectangles = [(x-width/2, metal_z[0], x+width/2, metal_z[1]) for x in centers]
    if rectangles_override is not None:
        rectangles=[tuple(r) for r in rectangles_override]
        if reflected: rectangles=[(-c,b,-a,d) for a,b,c,d in rectangles]
    validate_rectangles(rectangles,extent)
    patches = validate_dielectric_patches(dielectric_patches or [], extent)
    if reflected: patches = [(-c,b,-a,d,er) for a,b,c,d,er in patches]
    if max(abs(x) for r in rectangles for x in (r[0],r[2])) >= extent:
        raise ValueError('conductor intersects outer boundary')
    _start()
    try:
        occ = gmsh.model.occ
        wires = [(2, occ.addRectangle(a,b,0,c-a,d-b)) for a,b,c,d in rectangles]
        patch_shapes = [(2, occ.addRectangle(a,b,0,c-a,d-b)) for a,b,c,d,er in patches]
        pieces = []
        owners = []
        lower = 0.
        for upper, er in materials:
            plate = occ.addRectangle(-extent,lower,0,2*extent,upper-lower)
            cut, _ = occ.cut([(2,plate)], wires+patch_shapes, removeObject=True, removeTool=False)
            pieces.extend(cut); owners.extend([('background', len(owners), er)]*len(cut)); lower = upper
        # Record boolean fragment provenance instead of assigning nonconvex
        # regions from centroids, which can fall inside a conductor hole.
        for i, shape in enumerate(patch_shapes):
            cut, _ = occ.cut([shape], wires, removeObject=True, removeTool=False)
            if not cut: raise ValueError('dielectric patch has no area outside conductors')
            pieces.extend(cut); owners.extend([('patch', i, patches[i][4])]*len(cut))
        occ.remove(wires, recursive=True)
        if len(pieces)>1:
            fragmented, provenance = occ.fragment(pieces[:1], pieces[1:])
        else: fragmented=pieces; provenance=[pieces]
        occ.synchronize()
        epsmap = {}
        if patches:
            assigned = {}; by_er = {}
            for owner, children in zip(owners, provenance):
                er = owner[2]
                for dim, tag in children:
                    if dim != 2: continue
                    if tag in assigned and assigned[tag] != er: raise ValueError('ambiguous dielectric region')
                    assigned[tag] = er; by_er.setdefault(er, set()).add(tag)
            if set(assigned) != {tag for dim,tag in fragmented if dim == 2}:
                raise ValueError('dielectric fragment coverage incomplete')
            for idx, (er, surfaces) in enumerate(sorted(by_er.items())):
                name = f'eps_{idx}'; _group(2, sorted(surfaces), name); epsmap[name] = er
        else:
            # Keep the established horizontal-stack path unchanged.
            for idx, (upper, er) in enumerate(materials):
                lower = 0. if idx == 0 else materials[idx-1][0]
                surfaces = [tag for dim,tag in fragmented if dim == 2 and lower < occ.getCenterOfMass(dim,tag)[1] < upper]
                name = f'eps_{idx}'; _group(2, surfaces, name); epsmap[name] = er
        boundary = gmsh.model.getBoundary(fragmented, combined=True, oriented=False)
        groups = {f'c{i}': [] for i in range(len(wires))}; groups['ground'] = []
        for dim, tag in boundary:
            x,y,_,xx,yy,_ = gmsh.model.getBoundingBox(dim,tag)
            for i,(a,b,c,d) in enumerate(rectangles):
                if x >= a-1e-6 and xx <= c+1e-6 and y >= b-1e-6 and yy <= d+1e-6:
                    groups[f'c{i}'].append(tag); break
            else:
                if not (abs(x+extent)<1e-6 or abs(xx-extent)<1e-6 or abs(y)<1e-6 or abs(yy-extent)<1e-6):
                    raise ValueError('unclassified exterior facet')
                groups['ground'].append(tag)
        for name,tags in groups.items(): _group(1, tags, name)
        # Resolve corner singularities locally; far field can use larger cells.
        points = gmsh.model.getEntities(0)
        gmsh.model.mesh.setSize(points, h)
        field = gmsh.model.mesh.field.add('Distance')
        refined = list(range(len(rectangles))) if refine_conductor_indices is None else list(refine_conductor_indices)
        if not refined or any(i<0 or i>=len(rectangles) for i in refined): raise ValueError('invalid mesh-refinement electrode indices')
        gmsh.model.mesh.field.setNumbers(field, 'CurvesList', sum([groups[f'c{i}'] for i in refined], []))
        gmsh.model.mesh.field.setNumber(field, 'Sampling', 100)
        threshold = gmsh.model.mesh.field.add('Threshold')
        for key,val in [('InField',field),('SizeMin',h/3),('SizeMax',far_field_size or h*8),('DistMin',width),('DistMax',far_field_distance or extent/2)]:
            gmsh.model.mesh.field.setNumber(threshold,key,val)
        background=threshold
        # Give context plates their own boundary resolution, h rather than h/3.
        # Signal near fields retain the original fine scale; physical boundaries
        # and corner singularities are unchanged.
        unrefined=[i for i in range(len(rectangles)) if i not in refined]
        if unrefined:
            plate_distance=gmsh.model.mesh.field.add('Distance')
            gmsh.model.mesh.field.setNumbers(plate_distance,'CurvesList',sum([groups[f'c{i}'] for i in unrefined],[]))
            gmsh.model.mesh.field.setNumber(plate_distance,'Sampling',100)
            plate_threshold=gmsh.model.mesh.field.add('Threshold')
            for key,val in [('InField',plate_distance),('SizeMin',h),('SizeMax',far_field_size or h*8),('DistMin',width),('DistMax',far_field_distance or extent/2)]:
                gmsh.model.mesh.field.setNumber(plate_threshold,key,val)
            background=gmsh.model.mesh.field.add('Min')
            gmsh.model.mesh.field.setNumbers(background,'FieldsList',[threshold,plate_threshold])
        if corner_refinement:
            corner_points=[]
            for dim,tag in points:
                xyz=gmsh.model.getValue(dim,tag,[])
                if any(abs(xyz[0]-x)<1e-6 and abs(xyz[1]-y)<1e-6
                       for a,b,c,d in rectangles for x,y in [(a,b),(a,d),(c,b),(c,d)]):
                    corner_points.append(tag)
            if len(corner_points)!=4*len(rectangles): raise ValueError('missing conductor corner points')
            distance=gmsh.model.mesh.field.add('Distance')
            gmsh.model.mesh.field.setNumbers(distance,'PointsList',corner_points)
            local=gmsh.model.mesh.field.add('Threshold')
            for key,val in [('InField',distance),('SizeMin',h/100),('SizeMax',h/3),
                            ('DistMin',h/100),('DistMax',width*.2),('StopAtDistMax',1)]:
                gmsh.model.mesh.field.setNumber(local,key,val)
            near_fields=background
            background=gmsh.model.mesh.field.add('Min')
            gmsh.model.mesh.field.setNumbers(background,'FieldsList',[near_fields,local])
        gmsh.model.mesh.field.setAsBackgroundMesh(background)
        gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary', 0)
        gmsh.option.setNumber('Mesh.MeshSizeFromPoints', 0)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 0)
        gmsh.model.mesh.generate(2); gmsh.write(str(path))
    finally:
        gmsh.finalize()
    return epsmap, [f'c{i}' for i in range(len(rectangles))]


def validate_rectangles(rectangles, extent):
    if not rectangles: raise ValueError('no conductors')
    for i,r in enumerate(rectangles):
        if len(r)!=4 or not np.all(np.isfinite(r)): raise ValueError('finite rectangle coordinates required')
        a,b,c,d=r
        if not -extent<a<c<extent or not 0<b<d<extent:
            raise ValueError('invalid or boundary-touching conductor')
        for aa,bb,cc,dd in rectangles[:i]:
            if max(a,aa)<=min(c,cc) and max(b,bb)<=min(d,dd):
                raise ValueError('conductors overlap or touch')


def solve_mesh(path, permittivity, conductors, electrode_groups=None):
    mesh = MeshTri.load(str(path))
    if electrode_groups is not None:
        members=[v for group in electrode_groups.values() for v in group]
        if (not electrode_groups or 'ground' in electrode_groups or
            any(not group for group in electrode_groups.values()) or
            len(members)!=len(set(members)) or set(members)!=set(conductors)):
            raise ValueError('electrode groups must partition signal conductors exactly')
        mesh=mesh.with_boundaries({name:np.unique(np.concatenate([mesh.boundaries[v] for v in group]))
                                   for name,group in electrode_groups.items()})
        conductors=list(electrode_groups)
    basis = Basis(mesh, ElementTriP2(), intorder=4)
    epsilon = np.zeros(mesh.nelements)
    coverage = np.zeros(mesh.nelements, dtype=int)
    for name, er in permittivity.items():
        if not np.isfinite(er) or er <= 0: raise ValueError('invalid permittivity')
        idx = mesh.subdomains[name]; epsilon[idx] = EPS0*er; coverage[idx] += 1
    if not np.all(coverage == 1): raise ValueError('materials must partition all elements exactly')
    @BilinearForm
    def electrostatic(u,v,w): return w.epsilon*dot(grad(u),grad(v))
    stiffness = asm(electrostatic,basis,epsilon=epsilon[:,None]*np.ones_like(basis.dx))
    names = conductors+['ground']
    dofs = {name: basis.get_dofs(name).all() for name in names}
    if any(len(v)==0 for v in dofs.values()): raise ValueError('empty electrode')
    fixed = np.concatenate(list(dofs.values()))
    if len(np.unique(fixed)) != len(fixed): raise ValueError('electrodes touch')
    free = np.setdiff1d(np.arange(basis.N),fixed)
    lu = splu(stiffness[free][:,free].tocsc(), permc_spec='MMD_AT_PLUS_A', diag_pivot_thresh=0., options={'SymmetricMode': True})
    potentials = np.zeros((basis.N,len(conductors)))
    for j,name in enumerate(conductors): potentials[dofs[name],j] = 1.
    potentials[free,:] = lu.solve(-(stiffness[free][:,fixed] @ potentials[fixed,:]))
    reactions = stiffness @ potentials
    matrix = np.array([reactions[dofs[name]].sum(axis=0) for name in conductors])
    energy = potentials.T @ reactions
    # Independent strong-form boundary flux, not just another sum of K*u.
    flux = np.zeros_like(matrix)
    @Functional
    def boundary_charge(w): return w.epsilon*dot(w.uh.grad,w.n)
    for i,name in enumerate(conductors):
        fb = FacetBasis(mesh, ElementTriP2(),facets=mesh.boundaries[name],intorder=4)
        feps = epsilon[fb.tind][:,None]*np.ones_like(fb.dx)
        for j in range(len(conductors)):
            flux[i,j] = asm(boundary_charge,fb,uh=fb.interpolate(potentials[:,j]),epsilon=feps)
    scale = np.linalg.norm(matrix)
    off = matrix.copy(); np.fill_diagonal(off,0.)
    return {
        'matrix_F_per_m': matrix.tolist(), 'energy_matrix_F_per_m': energy.tolist(),
        'flux_matrix_F_per_m': flux.tolist(), 'conductors': conductors,
        'elements': int(mesh.nelements), 'dofs': int(basis.N),
        'diagnostics': {
            'reaction_energy_relative': float(np.linalg.norm(matrix-energy)/scale),
            'charge_energy_relative': float(np.linalg.norm(flux-energy)/scale),
            'reciprocity_relative': float(np.linalg.norm(matrix-matrix.T)/scale),
            'smallest_symmetric_eigenvalue_scaled': float(np.linalg.eigvalsh((matrix+matrix.T)/2).min()/scale),
            'max_positive_offdiagonal_scaled': float(max(0.,off.max())/scale),
            'min_ground_capacitance_scaled': float(matrix.sum(axis=1).min()/scale),
            'charge_conservation_scaled': float(np.linalg.norm(reactions[fixed].sum(axis=0))/scale),
            'free_residual_scaled': float(np.linalg.norm(reactions[free])/scale)
        }}


def run_case(spec, directory):
    path = Path(directory)/'mesh.msh'
    if spec['kind'] == 'coax':
        eps,names = coax_mesh(path,spec['h'],spec['er_inner'],spec['er_outer'])
        exact = 2*math.pi*EPS0/(math.log(1.5)/spec['er_inner']+math.log(2/1.5)/spec['er_outer'])
    elif spec['kind'] == 'wire':
        kwargs = {k:v for k,v in spec.items() if k not in ('kind','id','metadata','electrode_groups')}
        eps,names = wire_mesh(path,**kwargs); exact=None
    elif spec['kind'] == 'polygon':
        from .polygon_mesh import polygon_mesh
        kwargs={k:v for k,v in spec.items() if k not in ('kind','id','metadata')}
        eps,names=polygon_mesh(path,**kwargs);exact=None
    else: raise ValueError('unknown fixture')
    result = solve_mesh(path,eps,names,spec.get('electrode_groups'))
    if exact is not None:
        result['exact_F_per_m'] = exact
        result['analytic_relative_error'] = abs(result['matrix_F_per_m'][0][0]/exact-1.)
    return result
