"""SpriteCard secondary-frame zoom decoded from installed vertex shader.

Used with particle_sheet_table samples by the supported dual-sequence baker.
Atlas crop, material fades and the renderer's clock conversion are separate.
"""
import math
from particle_sheet_table import f32


def scale_parameters(zoom):
    zoom=float(zoom)
    if not math.isfinite(zoom):raise ValueError('Particle sequence zoom must be finite')
    if zoom<=1:return (1.,1.)
    inverse=f32(1./f32(zoom))
    return f32(f32(inverse+1.)*.5),inverse


def rectangle(rectangle,scale=1.):
    if len(rectangle)!=4 or not all(math.isfinite(float(v)) for v in (*rectangle,scale)):
        raise ValueError('Particle texture rectangle and scale must be finite')
    left,top,right,bottom=rectangle
    center_u,center_v=(left+right)*.5,(top+bottom)*.5
    half_u,half_v=(right-left)*.5*scale,(bottom-top)*.5*scale
    return ((center_u-half_u,1-center_v-half_v),(center_u+half_u,1-center_v-half_v),
            (center_u+half_u,1-center_v+half_v),(center_u-half_u,1-center_v+half_v))


def coordinates(primary,secondary,zoom=1.):
    fraction=secondary.blend
    if not math.isfinite(fraction) or not 0<=fraction<=1:
        raise ValueError('Secondary frame blend must be within 0..1')
    initial,final=scale_parameters(zoom)
    first_scale=initial+(final-initial)*fraction
    second_scale=1.+(initial-1.)*fraction
    return {'primary_current':rectangle(primary.current),
            'primary_following':rectangle(primary.following),
            'secondary_current':rectangle(secondary.current,first_scale),
            'secondary_following':rectangle(secondary.following,second_scale)}
