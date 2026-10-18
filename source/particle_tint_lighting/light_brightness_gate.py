"""Experimental ordinary world-light gate from 0x101944e4..0x10194552.

Runtime lightstyle value and minimum brightness must be supplied explicitly.
Does not infer console settings or implement surface/sky branches.
"""
import math
from particle_tint_lighting.point_light import f32

STYLE_SCALE=f32(0.0037878789007663727)

def apply(intensity,attenuation,*,style_value,minimum_brightness,bypass_style=False):
    if len(intensity)!=3 or any(not math.isfinite(v) for v in (*intensity,attenuation,minimum_brightness)):
        raise ValueError('Finite ordinary-light gate inputs required')
    if any(v<0 for v in intensity) or minimum_brightness<0:
        raise ValueError('Negative intensity or brightness threshold unverified')
    if type(style_value) is not int or type(bypass_style) is not bool:
        raise ValueError('Explicit integer runtime lightstyle and boolean bypass required')
    scaled=f32(attenuation)
    if not bypass_style:
        scaled=f32(f32(f32(style_value)*STYLE_SCALE)*scaled)
    brightness=f32(f32(max(intensity))*scaled)
    accepted=not f32(minimum_brightness)>brightness
    return {'accepted':accepted,'attenuation':scaled if accepted else 0.,
            'brightness':brightness}
