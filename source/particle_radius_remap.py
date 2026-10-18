"""Ordered radius state on the converter's approximate birth-relative clock.

Source tick phase is unverified. Creation time is immutable system time, not age.
"""
import math
from particle_scalar_remap import remap
from particle_radius_scale import sample


def scalar_state(modules,age,lifetime,initial_radius,creation_time,step=1/120,allow_signed=False,initial_trail=None):
    values=list(map(float,(age,lifetime,initial_radius,creation_time,step)))
    age,lifetime,initial_radius,creation_time,step=values
    if not all(math.isfinite(v) for v in values) or age<0 or lifetime<=0 or step<=0:
        raise ValueError('Invalid radius remap history interval')
    if initial_radius<0 and not allow_signed:raise ValueError('Invalid initial radius')
    ticks=math.floor(age/step)
    if ticks>1000000:raise ValueError('Radius remap history exceeds simulation limit')
    times=[i*step for i in range(ticks+1)]
    if times[-1]!=age:times.append(age)
    trail=None if initial_trail is None else float(initial_trail)
    if trail is not None and (not math.isfinite(trail) or trail<0):raise ValueError('Invalid initial trail duration')
    current=initial_radius;previous=0.
    for time in times:
        for module in modules:
            p=module['parameters'];name=module['function']
            if not p.get('operator enabled',True):continue
            if name=='Ramp Scalar Linear Random' and p.get('ramp field',3)==3:
                from particle_scalar_ramp import settings,step as ramp_step
                if any(p.get(name+' min',default)!=p.get(name+' max',default) for name,default in (('ramp rate',0),('start time',0),('end time',1))):
                    raise ValueError('Radius ramp requires persistent birth-sampled parameters')
                current=ramp_step(settings(p,(0.,0.,0.)),current,time,lifetime,time-previous)
            elif name=='Radius Scale':current=sample(p,time/lifetime,initial_radius,current)
            elif name=='Remap Scalar' and p['output field']==3:
                source={1:lifetime,3:current,8:creation_time}[p['input field']]
                current=remap(p,source,current)
            elif name=='Remap Scalar' and p['output field']==10 and trail is not None:
                source={1:lifetime,3:current,8:creation_time,10:trail}[p['input field']]
                trail=remap(p,source,trail)
            elif name=='Oscillate Scalar Simple' and int(p.get('oscillation field',7))==3:
                from particle_oscillation import delta
                current=max(0.,current+delta(p,time)-delta(p,previous))
            elif name=='Oscillate Scalar' and p.get('oscillation field',7)==3:
                from particle_scalar_oscillation import increment,f32
                current=f32(current+increment(p,time,lifetime,time-previous))
            elif name=='Oscillate Scalar Simple' and int(p.get('oscillation field',7))==10 and trail is not None:
                from particle_oscillation import delta
                trail=max(0.,trail+delta(p,time)-delta(p,previous))
            if not math.isfinite(current) or (current<0 and not allow_signed):
                raise ValueError('Invalid resulting radius remap')
            if trail is not None and (not math.isfinite(trail) or trail<0):raise ValueError('Invalid resulting trail duration')
        previous=time
    return current,trail


def radius(modules,age,lifetime,initial_radius,creation_time,step=1/120,allow_signed=False):
    return scalar_state(modules,age,lifetime,initial_radius,creation_time,step,allow_signed)[0]
