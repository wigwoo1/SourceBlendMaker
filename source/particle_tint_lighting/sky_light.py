"""Experimental sky query using an explicitly supplied surface trace provider."""
import math
from particle_tint_lighting.point_light import f32
from particle_tint_lighting.worldlight_visibility import TRACE_CONTENTS_MASK,sky_visible
SKY_RAY_LENGTH=f32(57016.3203125)

def query(point,normal,trace):
    if len(point)!=3 or len(normal)!=3 or any(not math.isfinite(v) for v in (*point,*normal)):
        raise ValueError('Finite sky-ray vectors required')
    if not callable(trace):raise ValueError('Sky surface trace provider required')
    point=tuple(map(f32,point));normal=tuple(map(f32,normal))
    end=tuple(f32(p-f32(n*SKY_RAY_LENGTH)) for p,n in zip(point,normal))
    result=trace(point,end,TRACE_CONTENTS_MASK)
    if not isinstance(result,dict) or 'surface_flags' not in result:
        raise ValueError('Sky trace must return explicit surface flags')
    visible=sky_visible(result['surface_flags'])
    return {'visible':visible,'incoming':tuple(-v for v in normal) if visible else (0.,0.,0.),
            'attenuation':1. if visible else 0.,'end':end,'trace_result':result}
