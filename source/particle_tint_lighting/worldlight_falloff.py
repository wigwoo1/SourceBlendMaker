"""Experimental point/spot formula prototype; shadows/styles are separate.

Distance has float32 vector arithmetic. Denominator/power precision is not an
emulation of Source's x87 runtime. No surface, sky or quakelight support here.
"""
import math
from particle_tint_lighting.point_light import f32

def distance_falloff(delta,constant,linear,quadratic,radius=0.,ignore_radius=False):
    if len(delta)!=3 or any(not math.isfinite(v) for v in (*delta,constant,linear,quadratic,radius)):
        raise ValueError('Finite light parameters required')
    if radius<0:raise ValueError('Negative light radius unsupported')
    delta=tuple(f32(v) for v in delta)
    squared=f32(f32(f32(delta[1]*delta[1])+f32(delta[0]*delta[0]))+f32(delta[2]*delta[2]))
    distance=f32(math.sqrt(squared))
    if not ignore_radius and radius!=0 and distance>f32(radius):return 0.
    denominator=f32(constant)+f32(linear)*distance+f32(quadratic)*squared
    # Installed point/spot branch takes the signed reciprocal without a clamp.
    # Zero-denominator engine floating-point behavior remains unimplemented.
    if denominator==0:raise ValueError('Undefined light falloff denominator')
    return 1./denominator

def spot_cone(cosine,inner,outer,exponent):
    if any(not math.isfinite(v) for v in (cosine,inner,outer,exponent)):
        raise ValueError('Finite cone parameters required')
    cosine,inner,outer,exponent=map(f32,(cosine,inner,outer,exponent))
    if not -1<=outer<=inner<=1 or exponent<0:raise ValueError('Invalid cone parameters')
    if cosine<=outer:return 0.
    if cosine>=inner:return 1.
    fraction=(cosine-outer)/(inner-outer)
    # The installed helper uses a linear ramp for exponents 0 and 1.
    return fraction if exponent in (0.,1.) else fraction**exponent
