"""Analytic non-overlapping linear emitter fades on collection simulation time.

This is an explicit approximation; Source tick/strength interpolation is unverified.
"""
import math
from particle_sim import Birth,continuous_births,simulation_at

KEYS=('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout')

def settings(p):
    values=tuple(float(p.get(key,0)) for key in KEYS)
    if any(not math.isfinite(v) or v<0 for v in values):raise ValueError('Invalid emitter fade times')
    a,b,c,d=values
    # Source's packed defaults and some installed PCFs leave the start field
    # nonzero while the corresponding end field is zero. A zero end disables
    # that fade (strength() already treats it as constant one), so discard the
    # orphaned start time before checking interval order.
    if b==0:a=b=0.
    if d==0:c=d=0.
    if b<a or d<c:raise ValueError('Descending emitter fade times are unsupported')
    values=(a,b,c,d)
    period=float(p.get('operator fade oscillate',0))
    if not math.isfinite(period) or period!=0:raise ValueError('Oscillating emitter strength is unsupported')
    if d and b>c:raise ValueError('Overlapping emitter fade ramps are unsupported')
    return values

def strength(values,t):
    a,b,c,d=values
    incoming=(min(1.,max(0.,(t-a)/(b-a))) if b>a else float(t>=a)) if b else 1.
    outgoing=(min(1.,max(0.,(d-t)/(d-c))) if d>c else float(t<c)) if d else 1.
    return incoming*outgoing

def continuous(segments,rate,p):
    values=settings(p)
    if not any(values):return continuous_births(segments,rate)
    # Existing clock validator also validates contiguous segments and speed bounds.
    continuous_births(segments,0)
    result=[];phase=0.
    for s in segments:
        lo_clock=simulation_at(segments,s.start);hi_clock=simulation_at(segments,s.end)
        if not s.emitting or not s.simulating or hi_clock<=lo_clock:continue
        points=sorted({lo_clock,hi_clock,*[v for v in values if lo_clock<v<hi_clock]})
        for a,b in zip(points,points[1:]):
            # Inside each interval the fade is linear; use one-sided values at steps.
            va=strength(values,math.nextafter(a,b));vb=strength(values,math.nextafter(b,a))
            slope=(vb-va)/(b-a)
            amount=rate*(va+vb)*(b-a)*.5
            count=math.floor(phase+amount+1e-10)
            if len(result)+count>1000000:raise ValueError('Particle bake exceeds configured particle limit')
            for i in range(count):
                target=(i+1-phase)/rate;x,y=0.,b-a
                for _ in range(50):
                    mid=(x+y)*.5
                    if va*mid+slope*mid*mid*.5<target:x=mid
                    else:y=mid
                clock=a+(x+y)*.5;x,y=s.start,s.end
                for _ in range(50):
                    mid=(x+y)*.5
                    if simulation_at(segments,mid)<clock:x=mid
                    else:y=mid
                result.append(Birth(len(result),(x+y)*.5,clock))
            phase+=amount-count
    return result
