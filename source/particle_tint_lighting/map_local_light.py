"""Experimental local point/spot inputs; not a complete particle light query."""
import math
from particle_tint_lighting.point_light import f32
from particle_tint_lighting.worldlight_falloff import distance_falloff,spot_cone
from particle_tint_lighting.surface_light import falloff as surface_falloff,angular as surface_angular

def local_input(light,point,*,ignore_radius):
    if light['type'] not in (0,1,2):raise ValueError('Only surface/point/spot local input implemented')
    if light['style']!=0:raise ValueError('Animated lightstyle not implemented')
    if type(ignore_radius) is not bool:raise ValueError('Explicit radius policy required')
    delta=tuple(f32(f32(a)-f32(b)) for a,b in zip(light['origin'],point))
    attenuation=(surface_falloff(delta,light['radius']) if light['type']==0 else
                 distance_falloff(delta,light['constant'],light['linear'],light['quadratic'],
                                  light['radius'],ignore_radius))
    length=math.sqrt(sum(v*v for v in delta))
    if not length:raise ValueError('Coincident light normalization policy unverified')
    incoming=tuple(f32(v/length) for v in delta)
    cone=1.
    if light['type']==0:
        cone=surface_angular(light['normal'],incoming,sum(v*v for v in incoming))
    if light['type']==2:
        cosine=-sum(a*b for a,b in zip(light['normal'],incoming))
        cone=spot_cone(cosine,light['inner'],light['outer'],light['exponent'])
    return {'incoming':incoming,'distance_attenuation':attenuation,
            'cone':cone,'contribution_scale':attenuation*cone}
