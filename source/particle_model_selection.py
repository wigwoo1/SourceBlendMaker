"""Default SFM hitbox selection from query slot 16 at 0x102d3bc0.

Four supplied random draws are consumed even with a desired hitbox. Source
random-table sequencing and collection call timing are not reproduced here.
Scale uses the installed endpoint mapping [1-scale, scale], including
coordinates outside the box. Installed SFM ignores direction bias and only
warns for the unimplemented surface-trace flag; other Source queries differ.
"""
import math
from particle_hitbox_lerp import f32

def select(parameters,count,rng):
    if type(count) is not int or count<=0:raise ValueError('Nonempty hitbox set required')
    scale=float(parameters.get('model hitbox scale',1))
    if not math.isfinite(scale) or scale<0:raise ValueError('Finite nonnegative model hitbox scale required')
    try:
        scale=f32(scale);minimum=f32(1.-scale);width=f32(scale-minimum)
    except OverflowError as exc:raise ValueError('Model hitbox scale exceeds float32 range') from exc
    if not all(math.isfinite(v) for v in (scale,minimum,width)):raise ValueError('Model hitbox scale exceeds float32 range')
    surface=parameters.get('force to be inside model',0)
    if not math.isfinite(float(surface)) or float(surface)!=int(surface) or not -(2**31)<=int(surface)<2**31:raise ValueError('Integer model surface-trace flag required')
    bias=tuple(parameters.get('direction bias',(0,0,0)))
    if len(bias)!=3 or not all(math.isfinite(float(v)) for v in bias):raise ValueError('Finite model direction bias required')
    desired=parameters.get('desired hitbox',-1)
    if isinstance(desired,bool) or not math.isfinite(float(desired)) or float(desired)!=int(desired):raise ValueError('Integer desired hitbox required')
    desired=int(desired)
    low=0 if desired<0 else min(desired,count-1)
    high=count-1 if desired<0 else low
    draws=[float(rng.random()) for _ in range(4)]
    if not all(math.isfinite(x) and 0<=x<1 for x in draws):raise ValueError('Random draws must lie in [0,1)')
    index=low+int(f32(f32(draws[0])*f32(high-low+1)))
    if index>high:raise ValueError('Float32 hitbox selection rounded beyond valid range')
    return dict(index=index,relative=tuple(f32(f32(f32(x)*width)+minimum) for x in draws[1:]))
