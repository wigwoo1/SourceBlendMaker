"""Scalar approximation of statically decoded nonlocal SFM pull arithmetic.

Double-precision math does not reproduce SSE reciprocal rounding exactly.
"""
import math,struct
from particle_pull_integrator import vec
EPSILON=2**-23
def encoded_exponent(power):
    power=float(power)
    if not math.isfinite(power):raise ValueError('Nonfinite falloff')
    try:single=struct.unpack('<f',struct.pack('<f',power))[0]
    except OverflowError:raise ValueError('Falloff outside float32 range')
    encoded=math.trunc(single*-4)
    if not -(2**31)<encoded<2**31:raise ValueError('Falloff outside supported integer encoding')
    return encoded
def acceleration(position,target,amount,power,component_scale=(1,1,1),strength=1):
    position=vec(position);target=vec(target);scale=vec(component_scale)
    amount=float(amount);strength=float(strength)
    if not math.isfinite(amount) or not math.isfinite(strength):raise ValueError('Nonfinite force magnitude')
    exponent=encoded_exponent(power)/4
    difference=tuple(b-a for a,b in zip(position,target));distance=math.hypot(*difference)
    if distance<=EPSILON:return (0.,0.,0.)
    magnitude=amount*strength*distance**exponent
    return vec(d/distance*magnitude*s for d,s in zip(difference,scale))
