"""Approximate birth-ordered parent collection view used by experimental baking.

This is not Source's active-buffer compaction or killed-parent dispatch view.
Only a complete simulation sampler may be supplied; renderer-applied locks or
constraints must be incorporated before this can represent those definitions.
"""
import math
from particle_parent_buffer import Snapshot


class Collection:
    def __init__(self,instance_id,births,lifetimes,origins,sampler,scale,*,deaths=None,radius_sampler=None):
        if not math.isfinite(scale) or scale<=0:raise ValueError('Positive finite simulation scale required')
        self.instance_id=instance_id
        self.births=tuple(births)
        self.lifetimes=dict(lifetimes)
        self.origins={key:tuple(value) for key,value in origins.items()}
        self.sampler=sampler;self.scale=scale
        self.deaths=deaths
        self.radius_sampler=radius_sampler
        ids=[birth.index for birth in self.births]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate parent birth identity')
        for birth in self.births:
            if birth.index not in self.lifetimes or birth.index not in self.origins:
                raise ValueError('Parent birth missing simulation inputs')
            life=self.lifetimes[birth.index]
            origin=self.origins[birth.index]
            if len(origin)!=3 or not all(math.isfinite(float(v)) for v in origin):
                raise ValueError('Finite three-component parent origin required')
            if not math.isfinite(life) or life<0 or not math.isfinite(birth.simulation_time):
                raise ValueError('Invalid parent lifetime or birth clock')
            if self.deaths is not None:self.deaths.register(birth.index,birth.simulation_time)

    def active(self,clock):
        if not math.isfinite(clock):raise ValueError('Finite parent clock required')
        for birth in self.births:
            age=clock-birth.simulation_time;life=self.lifetimes[birth.index]
            if not 0<=age<life:continue
            if self.deaths is not None and not self.deaths.alive(birth.index,clock):continue
            yield birth,age,life

    def scalar_values(self,field,clock):
        if field not in (1,3):raise ValueError('Parent scalar field is unsupported')
        if field==3 and self.radius_sampler is None:
            raise ValueError('Parent live radius history is unavailable')
        values=[]
        for birth,age,life in self.active(clock):
            value=life if field==1 else self.radius_sampler(birth,age,life)
            if not math.isfinite(value):raise ValueError('Finite parent attribute required')
            values.append(float(value))
        return tuple(values)

    def snapshot(self,clock,timestep):
        if not math.isfinite(clock) or not math.isfinite(timestep) or timestep<0:
            raise ValueError('Finite parent clock and nonnegative timestep required')
        ids=[];current=[];previous=[]
        for birth,age,life in self.active(clock):
            origin=self.origins[birth.index]
            now=self.sampler(birth,age,life)[0]
            old=self.sampler(birth,max(0.,age-timestep),life)[0]
            ids.append(birth.index)
            current.append(tuple((a+b)/self.scale for a,b in zip(origin,now)))
            previous.append(tuple((a+b)/self.scale for a,b in zip(origin,old)))
        return Snapshot.capture(self.instance_id,clock,ids,current,previous)
