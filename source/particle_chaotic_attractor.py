"""Installed Pickover recurrence, initializer 0x10220920.

Development arithmetic used by the particle baker.
Source float/trig approximation and random integer sampling are unverified.
"""
import math

def validate(parameters):
    from particle_epitrochoid import validate as validate_shared
    validate_shared({k:v for k,v in parameters.items() if k.startswith('operator ')})
    cp=float(parameters.get('Relative Control point number',0))
    scale=float(parameters.get('Scale',1))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64 or not math.isfinite(scale):
        raise ValueError('Invalid chaotic attractor control point/scale')
    following=step((0,0,0),parameters)
    velocity((0,0,0),following,parameters,.5)
    return int(cp)

def step(state,parameters):
    if len(state)!=3 or not all(math.isfinite(float(v)) for v in state):
        raise ValueError('Invalid chaotic attractor state')
    x,y,z=map(float,state)
    a,b,c,d=[float(parameters.get(k,v)) for k,v in (
        ('Pickover A Parameter',-.9629629),('Pickover B Parameter',2.791139),
        ('Pickover C Parameter',1.85185185),('Pickover D Parameter',1.5))]
    if not all(math.isfinite(v) for v in (a,b,c,d)):
        raise ValueError('Invalid chaotic attractor parameters')
    return (math.sin(a*y)-z*math.cos(b*x),
            z*math.sin(c*x)-math.cos(d*y),math.sin(x))

def velocity(state,following,parameters,unit):
    lo=float(parameters.get('Speed Min',0));hi=float(parameters.get('Speed Max',0))
    if not all(math.isfinite(v) for v in (lo,hi,unit)) or lo>hi or not 0<=unit<1:
        raise ValueError('Invalid chaotic attractor speed sample')
    # Installed code skips all speed work if max speed is effectively zero.
    if hi==0:return (0.,0.,0.)
    delta=[float(b)-float(a) for a,b in zip(state,following)]
    length=math.sqrt(sum(v*v for v in delta))
    # Installed branch normalizes when the authored Uniform speed flag is false.
    if not parameters.get('Uniform speed',False) and length>0:
        delta=[v/length for v in delta]
    minimum,maximum=math.trunc(lo),math.trunc(hi)
    speed=minimum+int(unit*(maximum-minimum+1))
    # Previous position is current + delta * speed * dt: velocity is negative.
    return tuple(-speed*v for v in delta)
