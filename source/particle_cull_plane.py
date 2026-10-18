"""Decoded Source plane-cull geometry used by shared lifecycle baking.

pet.dll 0x1027a070 normalizes a world-space normal, builds the plane at
CP - normal * offset, then queues particles on its negative side for death.
It checks current position, not a previous-to-current crossing. Source's SIMD
reciprocal-square-root approximation and exact boundary rounding are unverified.
"""
import math
from particle_scalar_oscillation import f32


def plane(control_position, normal=(0.,0.,1.), offset=0.):
    if len(control_position)!=3 or len(normal)!=3:
        raise ValueError('Plane requires XYZ control position and normal')
    if not all(math.isfinite(float(v)) for v in (*control_position,*normal,offset)):
        raise ValueError('Finite plane parameters required')
    cp=tuple(map(f32,control_position));n=tuple(map(f32,normal));offset=f32(offset)
    length=math.sqrt(sum(float(v)*v for v in n))
    if length==0:raise ValueError('Zero plane normal is unsupported')
    n=tuple(f32(v/length) for v in n)
    origin=tuple(f32(c-f32(v*offset)) for c,v in zip(cp,n))
    return origin,n


def negative_side(position, prepared):
    if len(position)!=3 or not all(math.isfinite(float(v)) for v in position):
        raise ValueError('Finite particle XYZ position required')
    origin,normal=prepared
    products=[f32(f32(f32(p)-o)*n) for p,o,n in zip(position,origin,normal)]
    distance=f32(f32(products[1]+products[0])+products[2])
    # Installed SIMD dispatch uses sign bits, not an ordinary <0 comparison.
    return math.copysign(1.,distance)<0


def settings(parameters):
    cp=parameters.get('Control Point for point on plane',0)
    if isinstance(cp,bool) or not math.isfinite(float(cp)) or float(cp)!=int(cp) or not 0<=int(cp)<64:
        raise ValueError('Cull plane control point must be within 0..63')
    normal=parameters.get('Plane Normal',(0.,0.,1.));offset=float(parameters.get('Cull plane offset',0.))
    plane((0,0,0),normal,offset)
    return {'control_point':int(cp),'normal':tuple(normal),'offset':offset}
