"""Installed-code scalar ramp arithmetic; Source random/tick parity unverified.

Injected random draws avoid claiming Source seed/table alignment. Clock inputs
must come from a chronological simulation; this is not an age-only closed form.
"""
import math,struct
MAX=3.4028234663852886e38
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]

def settings(p,draws):
 field=p.get('ramp field',3)
 if isinstance(field,bool) or field not in (1,3,4,5,7,10,12,16):raise ValueError('Unrepresented scalar ramp field')
 proportional=p.get('start/end proportional',True)
 if not isinstance(proportional,bool):raise ValueError('Invalid proportional flag')
 if len(draws)!=3 or any(not math.isfinite(v) or not 0<=v<=1 for v in draws):raise ValueError('Invalid random draws')
 sampled=[];bounds=[]
 for name,default,u in zip(('ramp rate','start time','end time'),(0,0,1),draws):
  lo=p.get(name+' min',default);hi=p.get(name+' max',default)
  if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (lo,hi)):raise ValueError('Invalid ramp range')
  # Installed SIMD computes low + draw*(high-low), without sorting bounds.
  # Several shipped spark effects intentionally use low=0, high=-1.
  lo,hi=f32(lo),f32(hi);bounds.append((lo,hi))
  sampled.append(f32(f32(f32(hi-lo)*f32(u))+lo))
 # Installed fast path skips the age-window mask for the default whole-life
 # proportional interval, including particles that survive their lifetime.
 gated=not(proportional and bounds[1]==(0.,0.) and bounds[2]==(1.,1.))
 if '_ramp_gated' in p:
  if not isinstance(p['_ramp_gated'],bool):raise ValueError('Invalid sampled ramp gate')
  gated=p['_ramp_gated']
 return dict(field=field,rate=sampled[0],start=sampled[1],end=sampled[2],proportional=proportional,gated=gated)

def step(s,current,age,lifetime,dt,strength=1.):
 if not all(math.isfinite(v) for v in (current,age,lifetime,dt,strength)) or age<0 or dt<0:raise ValueError('Invalid ramp clock/state')
 if lifetime<=0:return current
 clock=f32(age/lifetime) if s['proportional'] else f32(age)
 if s['gated'] and not s['start']<=clock<s['end']:return current
 increment=f32(f32(s['rate'])*f32(f32(dt)*f32(strength)))
 value=f32(f32(current)+increment)
 lo=0. if s['field'] in (3,7,10,16) else -MAX
 hi=1. if s['field'] in (7,16) else MAX
 return max(lo,min(hi,value))

class History:
 """Single-field chronological prototype; tick phase is approximate."""
 def __init__(self,s,initial,lifetime,tick_step=1/120):
  if not all(math.isfinite(v) for v in (initial,lifetime,tick_step)) or tick_step<=0:raise ValueError('Invalid history state')
  self.s=s;self.initial=initial;self.life=lifetime;self.step=tick_step
  self.tick=0;self.current=initial
 def query(self,age,strength=1.):
  if not math.isfinite(age) or age<0:raise ValueError('Invalid history age')
  target=math.floor(age/self.step)
  if target>1000000:raise ValueError('History simulation limit')
  # Strength is fixed for this query; changing it between calls must not reuse
  # a cached state simulated with a different strength.
  if target<self.tick or getattr(self,'strength',None)!=strength:
   self.tick=0;self.current=self.initial
  self.strength=strength
  while self.tick<target:
   self.tick+=1
   self.current=step(self.s,self.current,self.tick*self.step,self.life,self.step,strength)
  remainder=age-self.tick*self.step
  return step(self.s,self.current,age,self.life,remainder,strength) if remainder>0 else self.current


def validate_supported(parameters):
    result=settings(parameters,(.5,.5,.5))
    if result['field'] not in (3,4,12):raise ValueError('Scalar ramp currently supports radius, roll and yaw fields 3/4/12')
    from particle_color_timing import settings as timing,KEYS
    timing(parameters)
    if any(float(parameters.get(k,0))!=0 for k in KEYS):raise ValueError('Timed scalar ramp strength requires ordered integration')
    return result

def sample_operators(modules,rng):
    result={}
    for index,module in enumerate(modules):
        if module['function']!='Ramp Scalar Linear Random' or not module['parameters'].get('operator enabled',True):continue
        p=module['parameters'];validate_supported(p)
        s=settings(p,tuple(rng.random() for _ in range(3)))
        sampled=dict(p)
        sampled['_ramp_gated']=s['gated']
        for name,value in (('ramp rate',s['rate']),('start time',s['start']),('end time',s['end'])):
            sampled[name+' min']=sampled[name+' max']=value
        result[index]=sampled
    return result


def validate_radius(parameters):
    result=validate_supported(parameters)
    if result['field']!=3:raise ValueError('Radius validator requires field 3')
    return result
