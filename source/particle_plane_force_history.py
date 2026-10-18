"""Sparse fixed-tick history: cache fixed full ticks, never partial query steps."""
import math
from particle_plane_force import settings,acceleration_prepared


class History:
    def __init__(self,position,velocity,forces,target,gravity=(0,0,0),drag=0,birth_clock=0):
        self.latest=(tuple(map(float,position)),tuple(map(float,velocity)),0.)
        self.latest_tick=0;self.checkpoint_stride=30;self.states={0:self.latest}
        self.forces=[settings(p) for p in forces]
        self.target=target;self.gravity=tuple(map(float,gravity))
        self.drag=float(drag);self.birth_clock=float(birth_clock)
        position,velocity,_=self.latest
        if any(len(v)!=3 for v in (position,velocity,self.gravity)) or not all(math.isfinite(v) for v in position+velocity+self.gravity+(self.drag,self.birth_clock)) or self.drag<0:
            raise ValueError('Invalid plane-force history inputs')

    def step(self,state,end):
        position,velocity,t=state;dt=end-t
        def total(point,speed,clock):
            result=[self.gravity[i]-self.drag*speed[i] for i in range(3)]
            for p in self.forces:
                a=acceleration_prepared(point,self.target(p['Control point number'],self.birth_clock+clock),p)
                for i in range(3):result[i]+=a[i]
            return result
        a=total(position,velocity,t)
        midpoint=tuple(position[i]+velocity[i]*dt/2 for i in range(3))
        midspeed=tuple(velocity[i]+a[i]*dt/2 for i in range(3))
        middle_a=total(midpoint,midspeed,t+dt/2)
        position=tuple(position[i]+midspeed[i]*dt for i in range(3))
        velocity=tuple(velocity[i]+middle_a[i]*dt for i in range(3))
        return position,velocity,t+dt

    def query(self,age):
        age=float(age)
        if not math.isfinite(age) or age<0 or math.ceil(age*120)>100000:
            raise ValueError('Invalid history age')
        count=math.ceil(age*120)
        full=min(count,math.floor(age*120))
        while full and full/120>age:full-=1
        while full<count and (full+1)/120<=age:full+=1
        while self.latest_tick<full:
            self.latest_tick+=1
            self.latest=self.step(self.latest,self.latest_tick/120)
            if self.latest_tick%self.checkpoint_stride==0:self.states[self.latest_tick]=self.latest
        if full==self.latest_tick:state=self.latest
        else:
            checkpoint=(full//self.checkpoint_stride)*self.checkpoint_stride
            state=self.states[checkpoint]
            for tick in range(checkpoint,full):state=self.step(state,(tick+1)/120)
        for tick in range(full,count):state=self.step(state,min(age,(tick+1)/120))
        return state[:2]
