"""Fixed-subdivision plane death history shared by capacity and parent views.

Callbacks supply Source-space particle/control positions at simulation ages.
This is a converter approximation at 120 Hz, not Source engine tick parity.
The baker must register admitted births and advance before admission queries;
this adapter does not generate births or decide motion-operator ordering.
"""
import math
from particle_deaths import Deaths
from particle_cull_plane import plane,negative_side


class History:
    def __init__(self,position_at,control_at,*,normal=(0.,0.,1.),offset=0.,step=1/120):
        if not math.isfinite(step) or step<=0:raise ValueError('Positive finite cull step required')
        plane((0,0,0),normal,offset) # Validate configuration before sampling.
        self.position_at=position_at;self.control_at=control_at
        self.normal=tuple(normal);self.offset=offset;self.step=step
        self.deaths=Deaths();self._births={};self._checked={}
        self._version=0;self._advanced_version=-1;self._advanced_to=None

    def register(self,identity,birth_time):
        self.deaths.register(identity,birth_time)

    def add(self,birth,lifetime):
        life=float(lifetime)
        if not math.isfinite(life) or life<=0:raise ValueError('Positive finite authored lifetime required')
        if birth.index in self._births:raise ValueError('Cull birth already registered')
        self.register(birth.index,birth.simulation_time)
        self._births[birth.index]=(birth,life);self._checked[birth.index]=-1
        self._version+=1
        self._advanced_to=None

    def advance(self,clock):
        if not math.isfinite(float(clock)):raise ValueError('Finite cull simulation clock required')
        if self._advanced_version==self._version and self._advanced_to is not None and clock<=self._advanced_to:return
        for identity,(birth,life) in self._births.items():
            if self.deaths.time(identity) is not None:continue
            age=min(float(clock)-birth.simulation_time,life)
            if age<0:continue
            target=math.floor(age/self.step)
            while self._checked[identity]<target:
                index=self._checked[identity]+1;sample_age=index*self.step
                # Integer grid index makes query subdivision and rewind order
                # irrelevant. Never sample beyond the requested clock.
                if sample_age>age:break
                if sample_age>=life:
                    self._checked[identity]=target
                    break # Natural expiry is not an operator kill decision.
                point=self.position_at(birth,sample_age,life)
                origin=self.control_at(birth,sample_age)
                self._checked[identity]=index
                if negative_side(point,plane(origin,self.normal,self.offset)):
                    self.deaths.record(identity,birth.simulation_time,birth.simulation_time+sample_age)
                    break
        self._advanced_to=float(clock) if self._advanced_to is None else max(self._advanced_to,float(clock))
        self._advanced_version=self._version

    def alive(self,identity,clock):
        self.advance(clock)
        return self.deaths.alive(identity,clock)

    def time(self,identity):return self.deaths.time(identity)
    def events(self,cursor):return self.deaths.events(cursor)
