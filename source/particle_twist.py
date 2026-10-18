"""Investigative twist-force acceleration; not enabled by the bake planner.

Decoded from installed PET 0x101fb170. Exact Source reciprocal-square-root
rounding, local-axis basis and simulation integration remain unverified.
"""
import math
EPSILON=2**-23

def settings(parameters):
    amount=float(parameters.get('amount of force',0))
    axis=tuple(float(v) for v in parameters.get('twist axis',(0,0,1)))
    cp=float(parameters.get('control point',0))
    local=parameters.get('object local space axis 0/1',False)
    if len(axis)!=3 or not all(math.isfinite(v) for v in axis) or not math.isfinite(amount):
        raise ValueError('Invalid twist force or axis')
    length=math.hypot(*axis)
    if not math.isfinite(length) or length==0:raise ValueError('Zero or unrepresentable twist axis is unverified')
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:raise ValueError('Invalid twist control point')
    if local not in (False,True,0,1):raise ValueError('Invalid twist local-axis flag')
    return {'amount':amount,'axis':tuple(v/length for v in axis),'control_point':int(cp),'local_axis':bool(local)}

def acceleration(parameters,position,control_position):
    config=settings(parameters)
    if config['local_axis']:raise ValueError('Twist local-axis transform is not yet verified')
    p=tuple(float(v) for v in position);c=tuple(float(v) for v in control_position)
    if len(p)!=3 or len(c)!=3 or not all(math.isfinite(v) for v in p+c):raise ValueError('Invalid twist position')
    radial=tuple(a-b for a,b in zip(p,c));length=math.hypot(*radial)
    if not math.isfinite(length):raise ValueError('Unrepresentable twist displacement')
    if length<=math.sqrt(EPSILON):return (0.,0.,0.)
    radial=tuple(v/length for v in radial);axis=config['axis']
    # Preserve the decoded intermediate guard, rather than assume a standard
    # projection onto the plane perpendicular to the axis.
    dot=sum(a*b for a,b in zip(radial,axis))
    guarded=tuple(v*(1-dot) for v in radial);length2=sum(v*v for v in guarded)
    if length2<=EPSILON:return (0.,0.,0.)
    x,y,z=(v/math.sqrt(length2) for v in guarded);a,b,c=axis
    return tuple(v*config['amount'] for v in (y*c-z*b,z*a-x*c,x*b-y*a))

def trajectory(parameters,position,velocity,age,control_at_time,drag=0.,gravity=(0,0,0),step=1/120):
    """Offline midpoint prototype in Source units; callback takes particle age.

    Source tick rate, drag law and moving-control sampling remain unverified.
    """
    config=settings(parameters)
    if config['local_axis']:raise ValueError('Twist local-axis transform is not yet verified')
    age,drag,step=map(float,(age,drag,step))
    p=tuple(map(float,position));v=tuple(map(float,velocity));g=tuple(map(float,gravity))
    if any(len(a)!=3 for a in (p,v,g)) or not all(math.isfinite(x) for x in p+v+g+(age,drag,step)):
        raise ValueError('Invalid twist trajectory values')
    if age<0 or drag<0 or step<=0:raise ValueError('Invalid twist trajectory interval')
    count=math.ceil(age/step)
    if count>1000000:raise ValueError('Twist trajectory exceeds integration limit')
    if not count:return p,v
    dt=age/count
    def force(point,speed,time):
        twist=acceleration(parameters,point,control_at_time(time))
        return tuple(t+gravity-drag*speed for t,gravity,speed in zip(twist,g,speed))
    for tick in range(count):
        time=tick*dt;a=force(p,v,time)
        midpoint=tuple(x+speed*dt*.5 for x,speed in zip(p,v))
        middle_velocity=tuple(speed+acc*dt*.5 for speed,acc in zip(v,a))
        middle_force=force(midpoint,middle_velocity,time+dt*.5)
        p=tuple(x+speed*dt for x,speed in zip(p,middle_velocity))
        v=tuple(speed+acc*dt for speed,acc in zip(v,middle_force))
        if not all(math.isfinite(x) for x in p+v):raise ValueError('Nonfinite twist trajectory')
    return p,v
