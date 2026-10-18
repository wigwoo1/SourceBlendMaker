"""Secondary opacity history for installed Simple Scalar oscillation.

Static installed-engine evidence establishes initial 1, the parabolic wave,
collection-time phase, per-tick clamp, and primary * secondary rendering.
The converter's 120 Hz tick grid remains an approximation. Timed strengths
are rejected. Native original-effect validation is required before release.
"""
import math
from particle_scalar_oscillation import f32,wave

def settings(parameters):
    if parameters.get('oscillation field',7)!=16:
        raise ValueError('Secondary opacity requires scalar field 16')
    values=tuple(float(parameters.get(key,default)) for key,default in (
        ('oscillation rate',0),('oscillation frequency',1),
        ('oscillation multiplier',2),('oscillation start phase',.5)))
    if not all(math.isfinite(v) for v in values):raise ValueError('Invalid secondary opacity oscillator')
    # Timed strengths need the shared Source strength evaluator, not a gate.
    from particle_color_timing import settings as clock_settings,KEYS
    clock_settings(parameters)
    if any(float(parameters.get(key,0))!=0 for key in KEYS):
        raise ValueError('Timed secondary opacity strength is not yet supported')
    return tuple(f32(v) for v in values)

class History:
    def __init__(self,parameters,birth_time,step=1/120,initial=1.):
        self.oscillators=tuple(settings(p) for p in parameters if p.get('operator enabled',True))
        if not math.isfinite(birth_time) or not math.isfinite(step) or step<=0:
            raise ValueError('Invalid secondary opacity history clock')
        if not math.isfinite(initial) or not 0<=initial<=1:
            raise ValueError('Invalid initial secondary opacity')
        self.birth=birth_time;self.step=step;self.tick=0;self.initial=f32(initial);self.current=self.initial
    def advance(self,current,age,dt):
        clock=f32(self.birth+age)
        for rate,frequency,multiplier,phase in self.oscillators:
            argument=f32(f32(f32(clock*multiplier)+phase)*frequency)
            change=f32(f32(rate*f32(dt))*wave(argument))
            current=min(1.,max(0.,f32(current+change)))
        return current
    def query(self,age):
        if not math.isfinite(age) or age<0:raise ValueError('Invalid secondary opacity age')
        target=math.floor(age/self.step)
        if target>1000000:raise ValueError('Secondary opacity history exceeds simulation limit')
        if target<self.tick:self.tick=0;self.current=self.initial
        while self.tick<target:
            self.tick+=1
            self.current=self.advance(self.current,self.tick*self.step,self.step)
        remaining=age-self.tick*self.step
        return self.advance(self.current,age,remaining) if remaining>0 else self.current

def rendered_alpha(primary,secondary):
    if not all(math.isfinite(v) and 0<=v<=1 for v in (primary,secondary)):
        raise ValueError('Particle opacity outside normalized range')
    return f32(primary*secondary)
