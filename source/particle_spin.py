"""Analytic roll spin; linear slowdown is approximate, not Source tick parity.

Parameter meanings: official Dota particle operator documentation, Rotation
Spin Roll. It specifies the endpoint but not the interpolation curve.
"""
import math

def settings(parameters):
    values=tuple(float(parameters.get(key,0)) for key in
                 ('spin_rate_degrees','spin_stop_time','spin_rate_min'))
    if not all(math.isfinite(v) for v in values) or values[1]<0:
        raise ValueError('Invalid particle spin parameters')
    return values

def angle(parameters,age,creation_time=0.):
    rate,stop,minimum=settings(parameters)
    if not math.isfinite(age) or age<0:
        raise ValueError('Invalid particle spin age')
    from particle_emitter_fade import settings as fade_settings,strength
    fades=fade_settings(parameters)
    if any(fades):
        if not math.isfinite(creation_time) or creation_time<0:
            raise ValueError('Invalid particle spin creation time')
        points=sorted({0.,age,*([stop] if 0<stop<age else []),
                       *[v-creation_time for v in fades if 0<v-creation_time<age]})
        def value(t):
            speed=rate if stop==0 else rate+(minimum-rate)*min(t/stop,1.)
            return speed*strength(fades,creation_time+t)
        # Each interval is a product of two linear functions. Simpson's rule
        # integrates it exactly; one-sided endpoints preserve step fades.
        total=0.
        for a,b in zip(points,points[1:]):
            total+=(b-a)*(value(math.nextafter(a,b))+4*value((a+b)/2)+value(math.nextafter(b,a)))/6
        return math.radians(total)
    if stop==0:return math.radians(rate*age)
    ramp=min(age,stop)
    degrees=rate*ramp+(minimum-rate)*ramp*ramp/(2*stop)
    return math.radians(degrees+minimum*max(0,age-stop))
