"""Experimental installed lighting-cell bounds (0x10192950..0x10192a5f).

Negative coordinates exactly on a cell edge use the preceding cell. This
matches the sign/absolute-truncation branch, rather than ordinary floor.
Does not implement cache lookup, hashing, lifetime or gathering.
"""
import math
from particle_tint_lighting.point_light import f32

def bounds(point):
    if len(point)!=3 or any(not math.isfinite(v) for v in point):
        raise ValueError('Finite three-dimensional cache position required')
    low=[];high=[]
    for value,shift in zip(point,(5,5,7)):
        value=f32(value)
        if not math.isfinite(value) or abs(value)>=2147483648:
            raise ValueError('Cache integer conversion outside verified range')
        cell=int(abs(value))>>shift
        if value<0:cell=-1-cell
        edge=cell<<shift
        if not -2147483648<=edge<=2147483647:
            raise ValueError('Cache cell shift outside verified range')
        lower=f32(edge)
        low.append(lower);high.append(f32(lower+(1<<shift)))
    return tuple(low),tuple(high)
