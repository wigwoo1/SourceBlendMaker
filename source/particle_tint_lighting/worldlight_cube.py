"""Experimental directional color addition; attenuation/visibility are inputs."""
import math
from particle_tint_lighting.point_light import f32

def add(cube,directions,incoming,color,attenuation):
    if len(cube)!=len(directions) or not cube:raise ValueError('Directions and cube must agree')
    vectors=[*cube,*directions,incoming,color]
    if any(len(v)!=3 or any(not math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Finite RGB and vector inputs required')
    if not math.isfinite(attenuation) or attenuation<0:raise ValueError('Invalid attenuation')
    result=[]
    for base,direction in zip(cube,directions):
        dot=f32(f32(f32(direction[0]*incoming[0])+f32(direction[1]*incoming[1]))+f32(direction[2]*incoming[2]))
        amount=f32(dot*f32(attenuation)) if dot>0 else 0.
        result.append([f32(f32(base[i])+f32(f32(color[i])*amount)) for i in range(3)])
    return result
