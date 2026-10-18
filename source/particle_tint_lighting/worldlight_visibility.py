"""Experimental reduction of trace output; geometry tracing is supplied separately."""
import math
from particle_tint_lighting.point_light import f32
TRACE_CONTENTS_MASK=0x4481
ENDPOINT_TOLERANCE=8.

def point_visible(fraction,length):
    if not math.isfinite(fraction) or not 0<=fraction<=1 or not math.isfinite(length) or length<0:
        raise ValueError('Finite trace fraction and nonnegative length required')
    remaining=f32(f32(1.-f32(fraction))*f32(length))
    return remaining<=ENDPOINT_TOLERANCE

def sky_visible(surface_flags):
    if type(surface_flags) is not int or surface_flags<0:raise ValueError('Invalid surface flags')
    return bool(surface_flags&4)

def rank_score(rgb,attenuation):
    if len(rgb)!=3 or any(not math.isfinite(v) or v<0 for v in (*rgb,attenuation)):
        raise ValueError('Finite nonnegative ranking inputs required')
    red=f32(f32(rgb[0])*f32(.299))
    green=f32(f32(rgb[1])*f32(.587))
    blue=f32(f32(rgb[2])*f32(.114))
    return f32(f32(f32(green+red)+blue)*f32(attenuation))
