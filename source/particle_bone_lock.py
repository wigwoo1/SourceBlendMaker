"""Explicit-input bone-lock step from installed SFM function 0x10279880.

The caller must supply previous/current model points and control-point bypass
state. This kernel alone does not establish simulation cadence or graph support.
"""
import math
from particle_hitbox_lerp import f32

def weight(age, step, start=0., end=0., strength=1., *, bypass=False):
    if not all(math.isfinite(v) for v in (age,step,start,end,strength)):
        raise ValueError('Finite bone-lock timing required')
    if age<0 or step<=0 or not isinstance(bypass,bool):
        raise ValueError('Nonnegative age, positive step and explicit bypass required')
    age,step,start,end,strength=map(f32,(age,step,start,end,strength))
    if not all(math.isfinite(v) for v in (age,step,start,end,strength)) or step<=0:
        raise ValueError('Bone-lock timing exceeds float32 range')
    authored_end=end
    if end<=0:end=f32(1e20)
    if not bypass and age>=end:return 0.
    newborn=f32(f32(1./step)*min(age,step))
    if bypass or age<=start:return newborn
    reciprocal=f32(1./f32(authored_end-start)) if authored_end>start else 0.
    fade=f32(f32(1.-f32(f32(age-start)*reciprocal))*strength)
    return f32(newborn*fade)

def apply(position,previous_position,old_target,new_target,*,age,step,
          start=0.,end=0.,strength=1.,bypass=False,rigid=False):
    vectors=[tuple(v) for v in (position,previous_position,old_target,new_target)]
    if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Finite three-component bone-lock positions required')
    if not isinstance(rigid,bool):raise ValueError('Explicit rigid-lock flag required')
    w=weight(age,step,start,end,strength,bypass=bypass)
    # The installed ordinary branch skips the whole write at the fade endpoint.
    effective_end=f32(end) if end>0 else f32(1e20)
    if not bypass and f32(age)>=effective_end:return vectors[0],vectors[1]
    if rigid:
        target=tuple(f32(v) for v in vectors[3])
        return target,target
    delta=tuple(f32(f32(f32(b)-f32(a))*w) for a,b in zip(vectors[2],vectors[3]))
    return tuple(f32(f32(a)+d) for a,d in zip(vectors[0],delta)),tuple(f32(f32(a)+d) for a,d in zip(vectors[1],delta))
