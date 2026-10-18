"""Isolated pull integration; Source tick/trajectory semantics unverified.

All inputs/outputs are Source units. Recompute from birth for deterministic
queries. Midpoint integration uses a maximum 1/120 second step. Softening
The default decoded arithmetic uses statically inspected PET falloff encoding
and epsilon cutoff. Legacy softened arithmetic remains explicit for comparison.
"""
import math

def vec(value):
    value=tuple(float(v) for v in value)
    if len(value)!=3 or not all(math.isfinite(v) for v in value):
        raise ValueError('Expected three finite vector components')
    return value

def simulate(position,velocity,age,target,amount,power,gravity=(0,0,0),drag=0,step=1/120,softening=.01,component_scale=(1,1,1),strength=None,birth_clock=0,external_force=None,force_boundaries=(),arithmetic='decoded',spatial_force=None):
    position=vec(position);velocity=vec(velocity);gravity=vec(gravity);component_scale=vec(component_scale)
    age,amount,power,drag,step,softening,birth_clock=map(float,(age,amount,power,drag,step,softening,birth_clock))
    if not all(math.isfinite(v) for v in (age,amount,power,drag,step,softening,birth_clock)) or age<0 or drag<0 or step<=0 or softening<=0:
        raise ValueError('Invalid force simulation parameters')
    if arithmetic not in ('decoded','legacy_softened'):raise ValueError('Unknown pull arithmetic')
    if arithmetic=='decoded':
        from particle_pull_acceleration import acceleration as decoded_acceleration,encoded_exponent
        encoded_exponent(power)
    count=math.ceil(age/step)
    if count>100000:raise ValueError('Force simulation exceeds prototype step limit')
    boundaries=[float(t) for t in force_boundaries]
    if not all(math.isfinite(t) and 0<=t<=age for t in boundaries):
        raise ValueError('Force boundaries must be finite ages within the query interval')
    times=sorted(set([0.,age]+[index*step for index in range(1,count)]+boundaries))
    if len(times)>100002:raise ValueError('Force boundaries exceed prototype step limit')
    def acceleration(p,v,t):
        destination=vec(target(t))
        difference=tuple(b-a for a,b in zip(p,destination))
        distance=math.sqrt(sum(d*d for d in difference))
        fade=float(strength(birth_clock+t)) if strength else 1.
        if not math.isfinite(fade) or not 0<=fade<=1:raise ValueError('Invalid force strength')
        extra=vec(external_force(t)) if external_force else (0.,0.,0.)
        if spatial_force:
            spatial=vec(spatial_force(p,t))
            extra=vec(a+b for a,b in zip(extra,spatial))
        if arithmetic=='decoded':
            pull=decoded_acceleration(p,destination,amount,power,component_scale,fade)
            return vec(g+e-drag*w+f for g,e,w,f in zip(gravity,extra,v,pull))
        magnitude=amount*fade/max(distance,softening)**power
        # Scale after normalization: a hypothesis requiring Source comparison.
        result=tuple(g+e-drag*w+(d/distance*magnitude*c if distance else 0.) for g,e,w,d,c in zip(gravity,extra,v,difference,component_scale))
        return vec(result)
    for t,end in zip(times,times[1:]):
        dt=end-t
        a=acceleration(position,velocity,t)
        mid_position=tuple(p+v*dt*.5 for p,v in zip(position,velocity))
        mid_velocity=tuple(v+x*dt*.5 for v,x in zip(velocity,a))
        mid_acceleration=acceleration(mid_position,mid_velocity,t+dt*.5)
        position=vec(p+v*dt for p,v in zip(position,mid_velocity))
        velocity=vec(v+a*dt for v,a in zip(velocity,mid_acceleration))
    return position,velocity
