"""Experimental installed sphere/cone gate (0x1014e3e0..0x1014e57b).

Explicit sine/cosine inputs avoid claiming parity for engine x87 acos/fsin.
Does not construct cache bounds or apply the separate light-radius gate.
"""
import math
from particle_tint_lighting.point_light import f32

def sphere_cone(center,radius,apex,direction,*,sine,cosine):
    if any(len(v)!=3 for v in (center,apex,direction)):
        raise ValueError('Three-dimensional cone vectors required')
    if any(not math.isfinite(v) for vector in (center,apex,direction) for v in vector):
        raise ValueError('Finite cone vectors required')
    if not all(math.isfinite(v) for v in (radius,sine,cosine)):
        raise ValueError('Finite cone settings required')
    if radius<0 or sine<=0 or sine>1 or not -1<=cosine<=1:
        raise ValueError('Unsupported sphere radius or cone angles')
    center,apex,direction=(tuple(map(f32,v)) for v in (center,apex,direction))
    radius,sine,cosine=map(f32,(radius,sine,cosine))
    if sine==0:raise ValueError('Degenerate float32 cone sine')
    shift=f32(radius/sine)
    shifted=tuple(f32(p-f32(d*shift)) for p,d in zip(apex,direction))
    delta=tuple(f32(c-p) for c,p in zip(center,shifted))
    def length(v):
        return f32(math.sqrt(f32(f32(f32(v[1]*v[1])+f32(v[2]*v[2]))+f32(v[0]*v[0]))))
    def dot(v):
        return f32(f32(f32(direction[1]*v[1])+f32(direction[0]*v[0]))+f32(direction[2]*v[2]))
    if dot(delta)<f32(length(delta)*cosine):return False
    original=tuple(f32(c-p) for c,p in zip(center,apex))
    distance=length(original)
    if f32(-dot(original))>=f32(distance*sine) and radius<distance:return False
    return True
