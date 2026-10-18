"""Persistent first-impact tracking for particle collision development.

Position/radius callbacks describe simulation age in Source units. Samples use
fixed subdivisions; source engine tick/force/collision ordering is unverified.
"""
import math


class KillHistory:
    def __init__(self,position,radius,trace,step=1/120):
        if not math.isfinite(step) or step<=0:raise ValueError('Invalid collision history step')
        self.position,self.radius,self.trace=position,radius,trace
        self.step=step;self.checked_age=0.;self.death_age=None
        self.previous=self._position(0.)
        self.initial_checked=False

    def _position(self,age):
        value=tuple(map(float,self.position(age)))
        if len(value)!=3 or not all(math.isfinite(v) for v in value):raise ValueError('Invalid collision history position')
        return value

    def _radius(self,age):
        value=float(self.radius(age))
        if not math.isfinite(value) or value<0:raise ValueError('Invalid collision history radius')
        return value

    def _impact(self,start,end,radius,start_age,end_age):
        hit=self.trace(start,end,radius)
        if hit is None:return
        fraction=float(hit['fraction'])
        if not math.isfinite(fraction) or not 0<=fraction<=1:raise ValueError('Invalid collision trace fraction')
        self.death_age=start_age+(end_age-start_age)*fraction

    def alive(self,age):
        age=float(age)
        if not math.isfinite(age) or age<0:raise ValueError('Invalid collision history age')
        if not self.initial_checked:
            self._impact(self.previous,self.previous,self._radius(0.),0.,0.)
            self.initial_checked=True
        # Always advance on fixed boundaries. Reading age .003 before age .02
        # must not change the numerical path relative to reading .02 directly.
        while self.death_age is None and self.checked_age<age:
            next_age=(round(self.checked_age/self.step)+1)*self.step
            point=self._position(next_age)
            radius=max(self._radius(self.checked_age),self._radius(next_age))
            self._impact(self.previous,point,radius,self.checked_age,next_age)
            self.checked_age=next_age;self.previous=point
        return self.death_age is None or age<self.death_age
