"""Experimental translation-lock math; Source ticks and random stream unverified.

Integrate control-point displacement weighted by remaining attachment. Scaling
the entire birth-to-current displacement would incorrectly undo past motion.
History coordinates use particle simulation age, not scene frame numbers.
"""
import math

def validate(parameters):
    index=float(parameters.get('control_point_number',0))
    if not math.isfinite(index) or index!=int(index) or not 0<=index<64:
        raise ValueError('Invalid particle lock control point')
    if parameters.get('lock rotation',False) or float(parameters.get('distance fade range',0))!=0:
        raise ValueError('Experimental fade lock requires translation with no distance fade')
    threshold=float(parameters.get('instant jump threshold',512))
    if not math.isfinite(threshold) or threshold<0:raise ValueError('Invalid instant jump threshold')
    sampled_fades(parameters,.5,.5)
    return int(index),threshold

def history_displacement(segments,birth,current_time,lifetime,fade,position_at,threshold=512.,hz=120,prepared_inverse=None):
    """Approximate simulation-age history; exact Source tick phase unverified."""
    from particle_sim import simulation_at
    age=simulation_at(segments,current_time)-birth.simulation_time
    if age<=0:return (0.,0.,0.)
    count=max(1,math.ceil(age*hz));history=[]
    for i in range(count+1):
        target=age*i/count
        if i==0:time=birth.time
        elif i==count:time=current_time
        elif prepared_inverse is not None:
            time=prepared_inverse.query(birth.simulation_time+target,side='left',minimum_time=birth.time)
        else:
            lo,hi=birth.time,current_time
            for _ in range(40):
                middle=(lo+hi)*.5
                if simulation_at(segments,middle)-birth.simulation_time<target:lo=middle
                else:hi=middle
            time=(lo+hi)*.5
        history.append((target,position_at(time)))
    return displacement(history,lifetime,*fade,instant_jump_threshold=threshold)

def exponent_sample(unit,exponent):
    """Positive exponent path: installed SSE helper uses quarter steps."""
    if not math.isfinite(unit) or not 0<=unit<=1 or not math.isfinite(exponent) or exponent<=0:
        raise ValueError('Invalid positive fade random exponent')
    quarter=int(exponent*4)
    if quarter==0:return 1.
    # sqrt/square-and-multiply is represented algebraically here, not bitwise
    # SSE parity. Source's original random stream is deliberately not claimed.
    return unit**(quarter/4)

def sampled_fades(parameters,start_unit,end_unit):
    start_min=float(parameters.get('start_fadeout_min',1))
    start_max=float(parameters.get('start_fadeout_max',1))
    end_min=float(parameters.get('end_fadeout_min',1))
    end_max=float(parameters.get('end_fadeout_max',1))
    values=(start_min,start_max,end_min,end_max)
    if not all(math.isfinite(v) for v in values) or not 0<=start_min<=start_max<=end_min<=end_max<=1:
        raise ValueError('Unverified overlapping fade ranges')
    start=start_min+(start_max-start_min)*exponent_sample(start_unit,float(parameters.get('start_fadeout_exponent',1)))
    end=end_min+(end_max-end_min)*exponent_sample(end_unit,float(parameters.get('end_fadeout_exponent',1)))
    return start,end

def displacement(history,lifetime,start_fraction,end_fraction,instant_jump_threshold=512.):
    values=(lifetime,start_fraction,end_fraction,instant_jump_threshold)
    if not all(math.isfinite(v) for v in values) or lifetime<=0 or instant_jump_threshold<0 or not 0<=start_fraction<=end_fraction<=1:
        raise ValueError('Invalid lifetime/fade interval')
    history=list(history)
    if not history:return (0.,0.,0.)
    for age,position in history:
        if not math.isfinite(age) or age<0 or len(position)!=3 or not all(math.isfinite(v) for v in position):
            raise ValueError('Invalid control history sample')
    start,end=start_fraction*lifetime,end_fraction*lifetime
    result=[0.,0.,0.]
    def weight(age):
        if age<start:return 1.
        if age>=end:return 0.
        return (end-age)/(end-start)
    for (a,p),(b,q) in zip(history,history[1:]):
        if b<a:raise ValueError('Control history must be chronological')
        if b==a:
            if tuple(p)!=tuple(q):raise ValueError('Conflicting same-age control samples')
            continue
        # Installed jump branch bypasses age fading, retaining unit attachment.
        # Positions and threshold here are both Source units. Engine checks
        # per-tick deltas; this prototype only checks the supplied history.
        jump=math.dist(p,q)>instant_jump_threshold
        # Split fade boundaries; trapezoid is exact for this linear candidate.
        knots=[a]+[v for v in (start,end) if a<v<b]+[b]
        knots=sorted(set(knots))
        amount=1. if jump else sum((hi-lo)*(weight(lo)+weight(hi))*.5 for lo,hi in zip(knots,knots[1:]))/(b-a)
        for axis in range(3):result[axis]+=(q[axis]-p[axis])*amount
    return tuple(result)
