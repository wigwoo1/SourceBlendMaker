"""Normal initializer arithmetic prototype, not production particle support.

Caller supplies the sampled control-point basis and sampled random offset.
Source RNG, basis selection and normal-lock animation remain unverified.
"""
import math
from particle_ring import rotate

def vector(value):
    result=tuple(map(float,value))
    if len(result)!=3 or not all(math.isfinite(v) for v in result):
        raise ValueError('Invalid particle normal vector')
    return result

def locked(normal,previous_rotation,current_rotation,age,tick_delta):
    """Disabled prototype of the installed normal-lock operator's rotation lerp.

    Input bases must be rigid control-point rotations. Translation does not
    affect normals. Source clock sampling and renderer integration are pending.
    """
    normal=vector(normal);age=float(age);tick_delta=float(tick_delta)
    if not math.isfinite(age) or age<0 or not math.isfinite(tick_delta) or tick_delta<=0:
        raise ValueError('Normal locking requires a nonnegative age and positive tick')
    previous=tuple(vector(row) for row in previous_rotation)
    current=tuple(vector(row) for row in current_rotation)
    if len(previous)!=3 or len(current)!=3:
        raise ValueError('Normal locking requires two rotation matrices')
    local=rotate(tuple(zip(*previous)),normal)
    transformed=rotate(current,local)
    amount=min(age,tick_delta)/tick_delta
    return tuple(a+(b-a)*amount for a,b in zip(normal,transformed))

def align(control_forward):
    """Copy the caller-resolved control-point forward vector."""
    return vector(control_forward)

def offset(normal,sampled_offset,parameters,control_rotation=None):
    normal=vector(normal);sampled_offset=vector(sampled_offset)
    if parameters.get('offset in local space 0/1',False):
        if control_rotation is None:raise ValueError('Local normal offset requires a control-point basis')
        sampled_offset=rotate(control_rotation,sampled_offset)
    result=tuple(a+b for a,b in zip(normal,sampled_offset))
    if parameters.get('normalize output 0/1',False):
        length=math.hypot(*result)
        if length:result=tuple(v/length for v in result)
    return result
