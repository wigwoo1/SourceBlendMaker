"""Scalar oscillation; approximate birth-relative 120 Hz clock.

Wave arithmetic follows inspected SFM SSE code. Random ranges use sampled
converter RNG values; Source random alignment and tick timing are unverified.
"""
import math,struct

# SFM omits these members when they match its serialized operator defaults.
# Defaults are verified against installed PET metadata builder 0x1023e160,
# reached through the factory metadata pointer 0x10506da0. See
# diagnostics/scalar_metadata_defaults_20261015.json for the read-only trace.
SOURCE_OMITTED_DEFAULTS={
    'oscillation field':7,
    'oscillation rate min':0.0,'oscillation rate max':0.0,
    'oscillation frequency min':1.0,'oscillation frequency max':1.0,
    'proportional 0/1':True,
    'start/end proportional':True,
    'oscillation multiplier':2.0,
    'oscillation start phase':0.5,
    'start time min':0.0,'start time max':0.0,
    'end time min':1.0,'end time max':1.0,
}

def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]

def settings(p,allow_random=False):
    if any(key not in p for key in SOURCE_OMITTED_DEFAULTS):
        p={**SOURCE_OMITTED_DEFAULTS,**p}
    required=('oscillation field','proportional 0/1','start/end proportional','oscillation multiplier','oscillation start phase')
    required+=tuple(name+suffix for name in ('oscillation rate','oscillation frequency','start time','end time') for suffix in (' min',' max'))
    if any(key not in p for key in required):raise ValueError('Full scalar oscillation requires explicit parameters')
    field=p['oscillation field']
    if isinstance(field,bool) or not isinstance(field,(int,float)) or field not in (3,4,7):raise ValueError('Full scalar oscillation currently supports radius, roll and alpha fields 3/4/7')
    if any(not isinstance(p[key],bool) for key in ('proportional 0/1','start/end proportional')):raise ValueError('Invalid oscillation clock flag')
    for key in required:
        if key in ('proportional 0/1','start/end proportional'):continue
        if isinstance(p[key],bool) or not isinstance(p[key],(int,float)) or not math.isfinite(p[key]):raise ValueError('Invalid oscillation scalar parameter')
    for name in ('oscillation rate','oscillation frequency','start time','end time'):
        if p[name+' min']>p[name+' max']:raise ValueError('Invalid oscillation parameter range')
        if not allow_random and p[name+' min']!=p[name+' max']:raise ValueError('Full scalar oscillation requires sampled birth parameters')
    if p['start time max']>p['end time min']:raise ValueError('Overlapping randomized oscillation window remains unverified')
    return p

def sample(p,rng):
    result=dict(settings(p,allow_random=True))
    for name in ('oscillation frequency','oscillation rate','start time','end time'):
        low,high=result[name+' min'],result[name+' max']
        value=low if low==high else rng.uniform(low,high)
        result[name+' min']=result[name+' max']=value
    return result

def wave(phase):
    phase=f32(phase)
    if not math.isfinite(phase) or abs(phase)>=2**22:raise ValueError('Oscillation phase outside verified wave scope')
    x=abs(phase)%2;negative=x>=1
    if negative:x=f32(x-1)
    result=f32(f32(4-f32(x*4))*x)
    return -result if negative!=(phase<0) else result

def increment(p,age,lifetime,dt):
    if any(key not in p for key in SOURCE_OMITTED_DEFAULTS):p=settings(p)
    clock=age/lifetime if p['start/end proportional'] else age
    if not p['start time min']<=clock<p['end time min']:return 0.
    phase=age*p['oscillation frequency min']
    if p['proportional 0/1']:phase=phase/lifetime*p['oscillation multiplier']+p['oscillation start phase']
    return f32(wave(phase)*f32(p['oscillation rate min']*dt))

def delta(p,age,lifetime,step=1/120):
    settings(p)
    if not all(math.isfinite(v) for v in (age,lifetime,step)) or age<0 or lifetime<=0 or step<=0:raise ValueError('Invalid oscillation interval')
    ticks=math.floor(age/step)
    if ticks>1000000:raise ValueError('Oscillation history exceeds simulation limit')
    current=0.;previous=0.
    times=[i*step for i in range(1,ticks+1)]
    if not times or times[-1]<age:times.append(age)
    for time in times:
        current=f32(current+increment(p,time,lifetime,time-previous))
        previous=time
    return current
