"""Experimental surface-light distance/angular arithmetic; no query caches."""
import math
from particle_tint_lighting.point_light import f32

def falloff(delta,radius):
    if len(delta)!=3 or any(not math.isfinite(v) for v in (*delta,radius)) or radius<0:
        raise ValueError('Finite surface delta and nonnegative radius required')
    x,y,z=map(f32,delta)
    squared=f32(f32(f32(x*x)+f32(y*y))+f32(z*z))
    if radius and squared>f32(f32(radius)*f32(radius)):return 0.
    return 1./max(1.,squared)

def angular(normal,incoming,diffuse_factor):
    if len(normal)!=3 or len(incoming)!=3 or any(not math.isfinite(v) for v in (*normal,*incoming,diffuse_factor)):
        raise ValueError('Finite surface angular inputs required')
    if diffuse_factor<0:return 0.
    facing=-sum(f32(a)*f32(b) for a,b in zip(normal,incoming))
    return facing*diffuse_factor if facing>.01 else 0.
