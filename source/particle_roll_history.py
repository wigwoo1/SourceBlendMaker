"""Ordered particle roll history; radians at the scalar operator boundary.

Source scalar-ramp operating code contains no angular conversion. Serialized
metadata declares ordinary float rates. Source RNG/tick parity is unverified.
"""
import math
from particle_scalar_ramp import settings,step,f32
class History:
 def __init__(self,modules,initial,lifetime,rotation_speed=0.,creation_time=0.,tick_step=1/120,field=4):
  if not all(math.isfinite(v) for v in (initial,lifetime,rotation_speed,creation_time,tick_step)) or lifetime<=0 or tick_step<=0:raise ValueError('Invalid ordered roll history')
  if field not in (4,12):raise ValueError('Angular history supports roll/yaw only')
  self.field=field
  self.modules=modules;self.initial=initial;self.life=lifetime;self.speed=rotation_speed
  self.creation=creation_time;self.step=tick_step;self.tick=0;self.current=initial
 def advance(self,current,time,previous):
  dt=time-previous
  for module in self.modules:
   name=module['function'];p=module['parameters']
   if not p.get('operator enabled',True):continue
   if name=='Ramp Scalar Linear Random' and p.get('ramp field',3)==self.field:
    if any(p.get(n+' min',d)!=p.get(n+' max',d) for n,d in (('ramp rate',0),('start time',0),('end time',1))):raise ValueError('Angular ramp requires sampled birth parameters')
    current=step(settings(p,(0,0,0)),current,time,self.life,dt)
   elif self.field==4 and name=='Rotation Basic':current=f32(current+f32(math.radians(self.speed)*dt))
   elif self.field==4 and name=='Rotation Spin Roll':
    from particle_spin import angle
    current=f32(current+f32(angle(p,time,self.creation)-angle(p,previous,self.creation)))
   elif self.field==4 and name=='Oscillate Scalar' and p.get('oscillation field')==4:
    from particle_scalar_oscillation import increment
    current=f32(current+increment(p,time,self.life,dt))
  if not math.isfinite(current):raise ValueError('Nonfinite roll result')
  return current
 def query(self,age):
  if not math.isfinite(age) or age<0:raise ValueError('Invalid roll age')
  target=math.floor(age/self.step)
  if target>1000000:raise ValueError('Roll simulation limit')
  if target<self.tick:self.tick=0;self.current=self.initial
  while self.tick<target:
   previous=self.tick*self.step;self.tick+=1
   self.current=self.advance(self.current,self.tick*self.step,previous)
  return self.advance(self.current,age,self.tick*self.step) if age>self.tick*self.step else self.current
