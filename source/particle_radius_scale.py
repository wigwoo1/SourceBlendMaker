"""Radius writes and approximate fixed-clock history for offline baking.

Caller supplies persistent current radius and immutable birth radius.
Exact Source simulation tick phase is not claimed here.
"""
import math
from particle_radius_bias import interpolate

def sample(parameters,fraction,initial_radius,current_radius):
    start=float(parameters.get('start_time',0));end=float(parameters.get('end_time',1))
    low=float(parameters.get('radius_start_scale',1));high=float(parameters.get('radius_end_scale',1))
    fraction,initial_radius,current_radius=map(float,(fraction,initial_radius,current_radius))
    if not all(math.isfinite(x) for x in (start,end,low,high,fraction,initial_radius,current_radius)):
        raise ValueError('Nonfinite radius scale values')
    if start>=end or not start<=fraction<end:return current_radius
    amount=interpolate((fraction-start)/(end-start),parameters.get('scale_bias',.5),parameters.get('ease_in_and_out',False))
    return initial_radius*(low+(high-low)*amount)

def ordered_sample(modules,fraction,initial_radius,current_radius):
    for module in modules:
        if module['function']=='Radius Scale' and module['parameters'].get('operator enabled',True):
            current_radius=sample(module['parameters'],fraction,initial_radius,current_radius)
    return current_radius

def history(modules,fractions,initial_radius):
    """Replay caller-supplied ordered simulation samples, preserving radius."""
    current=float(initial_radius);previous=-math.inf;results=[]
    if not math.isfinite(current) or current<0:raise ValueError('Invalid initial radius')
    for fraction in fractions:
        fraction=float(fraction)
        if not math.isfinite(fraction) or fraction<0 or fraction<previous:
            raise ValueError('Radius history samples must be finite and ordered')
        current=ordered_sample(modules,fraction,initial_radius,current)
        if not math.isfinite(current) or current<0:raise ValueError('Invalid resulting radius')
        results.append(current);previous=fraction
    return results

def sampled_radius(modules,age,lifetime,initial_radius,step=1/120,allow_signed_radius=False):
    """Equivalent to replay on a birth-relative fixed clock plus final sample.

    Find the latest active write without walking every intermediate tick.
    Source clock phase remains approximate; other radius operators are excluded.
    """
    age,lifetime,initial_radius,step=map(float,(age,lifetime,initial_radius,step))
    if not all(math.isfinite(v) for v in (age,lifetime,initial_radius,step)) or age<0 or lifetime<=0 or step<=0 or (initial_radius<0 and not allow_signed_radius):
        raise ValueError('Invalid radius history interval')
    last=None;result=initial_radius
    for index,module in enumerate(modules):
        if module['function']!='Radius Scale' or not module['parameters'].get('operator enabled',True):continue
        p=module['parameters'];start=float(p.get('start_time',0));end=float(p.get('end_time',1))
        if not math.isfinite(start) or not math.isfinite(end):raise ValueError('Invalid radius scale interval')
        if start>=end:continue
        if start<=age/lifetime<end:candidate=age
        else:
            # Strictly less than end, including when it lies exactly on a tick.
            tick=min(math.floor(age/step),math.ceil(end*lifetime/step)-1)
            while tick>=0 and tick*step/lifetime>=end:tick-=1
            candidate=tick*step
            if tick<0 or not start<=candidate/lifetime<end:continue
        key=(candidate,index)
        if last is None or key>last:
            result=sample(p,candidate/lifetime,initial_radius,result);last=key
    return result

def mixed_radius(modules,age,lifetime,initial_radius,step=1/120):
    """Ordered replay of scales and analytic oscillation increments.

    Source oscillation phase and discrete integration are approximate.
    """
    from particle_oscillation import delta
    age,lifetime,initial_radius,step=map(float,(age,lifetime,initial_radius,step))
    if not all(math.isfinite(v) for v in (age,lifetime,initial_radius,step)) or age<0 or lifetime<=0 or step<=0 or initial_radius<0:
        raise ValueError('Invalid mixed radius history interval')
    ticks=math.floor(age/step)
    if ticks>1000000:raise ValueError('Mixed radius history exceeds simulation limit')
    times=[tick*step for tick in range(ticks+1)]
    if times[-1]!=age:times.append(age)
    previous=0.;radius=initial_radius
    for time in times:
        for module in modules:
            p=module['parameters']
            if not p.get('operator enabled',True):continue
            if module['function']=='Radius Scale':radius=sample(p,time/lifetime,initial_radius,radius)
            elif module['function']=='Oscillate Scalar Simple' and int(p.get('oscillation field',7))==3:
                radius=max(0.,radius+delta(p,time)-delta(p,previous))
            if not math.isfinite(radius) or radius<0:raise ValueError('Invalid mixed radius result')
        previous=time
    return radius
