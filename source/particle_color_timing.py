"""Installed Color Fade activation gate; approximate 120 Hz collection clock.

Shared helper101ebe20/ramp101e9cf0 and cache101f076b were inspected
statically. Random clock transforms, cap states and CP strength are rejected.
"""
import math,struct
KEYS=('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout')
def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def settings(p):
    defaults={'operator time offset min':0,'operator time offset max':0,
              'operator time scale min':1,'operator time scale max':1,
              'operator strength random scale min':1,'operator strength random scale max':1,
              'operator time strength random scale max':1,'operator fade oscillate':0,
              'operator strength scale control point':-1,'operator end cap state':-1}
    if any(float(p.get(k,v))!=v for k,v in defaults.items()):
        raise ValueError('Color Fade transformed clock or external strength is unsupported')
    values=tuple(f32(float(p.get(k,0))) for k in KEYS)
    if any(not math.isfinite(v) or v<0 for v in values):raise ValueError('Invalid Color Fade activation times')
    return values
def active(p,time):
    a,b,c,d=settings(p);time=f32(time)
    if not math.isfinite(time):raise ValueError('Invalid Color Fade collection time')
    # Cached unconditional flag intentionally does not inspect end fadein.
    if a==c==d==0:return True
    if a>time or (d>0 and time>d):return False
    b=max(b,a);c=max(c,b);d=max(d,c);strength=1.
    if b>time and b>a:strength=min(strength,f32(f32(time-a)/f32(b-a)))
    if time>c and d>c:strength=min(strength,f32(f32(time-d)/f32(c-d)))
    return strength>0
class History:
    def __init__(self,initial,target,lifetime,parameters,birth_time,step=1/120):
        settings(parameters)
        if not all(math.isfinite(v) for v in (lifetime,birth_time,step)) or lifetime<=0 or step<=0:raise ValueError('Invalid Color Fade history clock')
        self.initial=tuple(initial);self.target=tuple(target);self.life=lifetime
        self.parameters=dict(parameters);self.birth=birth_time;self.step=step
        self.tick=0;self.current=self.initial
        self.current=self.write(self.initial,0.)
    def write(self,current,time):
        from particle_color_fade import color
        if not active(self.parameters,self.birth+time):return current
        return color(self.initial,self.target,time/self.life,self.parameters,current=current)
    def query(self,age):
        if not math.isfinite(age) or age<0:raise ValueError('Invalid Color Fade age')
        target=math.floor(age/self.step)
        if target>1000000:raise ValueError('Color Fade history exceeds simulation limit')
        if target<self.tick:self.tick=0;self.current=self.write(self.initial,0.)
        while self.tick<target:
            self.tick+=1;self.current=self.write(self.current,self.tick*self.step)
        return self.write(self.current,age) if age>self.tick*self.step else self.current
