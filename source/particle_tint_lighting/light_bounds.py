"""Experimental point-light bounds gate from installed engine static evidence.

Caller must provide cache bounds and the runtime radius multiplier. Cache
construction and surface/spot cone gates are not implemented here.
"""
import math
from particle_tint_lighting.point_light import f32

def distance_squared(low,high,point):
    if any(len(v)!=3 for v in (low,high,point)):
        raise ValueError('Three-dimensional bounds required')
    if any(not math.isfinite(x) for v in (low,high,point) for x in v):
        raise ValueError('Finite bounds required')
    low,high,point=(tuple(map(f32,v)) for v in (low,high,point))
    if any(a>b for a,b in zip(low,high)):
        raise ValueError('Inverted bounds')
    total=0.
    for a,b,p in zip(low,high,point):
        delta=f32(a-p) if a>p else f32(p-b) if p>b else 0.
        total=f32(total+f32(delta*delta))
    return total

def point_eligible(low,high,origin,radius,*,radius_multiplier):
    if any(not math.isfinite(v) or v<0 for v in (radius,radius_multiplier)):
        raise ValueError('Finite nonnegative radius settings required')
    distance=distance_squared(low,high,origin)
    limit=f32(f32(f32(radius)*f32(radius))*f32(radius_multiplier))
    return dict(eligible=distance<=limit,distance_squared=distance,limit=limit,
                cache_constructed=False)
