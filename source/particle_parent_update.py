"""Chronological parent-vector copying on the converter's approximate 120 Hz clock.

PET update 0x10263060 supplies copy/cursor rules. Active slots are birth ordered,
not Source's compacted buffers; exact engine tick/RNG parity is unverified.
"""
import math
import random
from particle_scalar_oscillation import f32
from particle_vector_history import movement,vector
from particle_parent_attribute import Initializer

NAME='Inherit Attribute From Parent Particle'
COSMETIC={'Lifespan Decay','Radius Scale','Alpha Fade In Simple','Alpha Fade Out Simple',
          'Alpha Fade In Random','Alpha Fade Out Random','Alpha Fade and Decay','Color Fade',
          'Rotation Basic','Rotation Spin Roll','Ramp Scalar Linear Random','Remap Scalar',
          'Oscillate Scalar','Oscillate Scalar Simple'}


def prepare(definition):
    modules=[m for m in definition['modules']['operators'] if m['parameters'].get('operator enabled',True)]
    copies=[m for m in modules if m['function']==NAME]
    if not copies:return []
    if any(definition['modules'].get(g) for g in ('forces','constraints')):
        raise ValueError('Parent vector copying with forces/constraints requires ordered integration')
    for m in modules:
        if m['function'] not in COSMETIC|{NAME,'Movement Basic'}:
            raise ValueError('Parent vector copying with '+m['function']+' requires ordered integration')
        if m['function']==NAME:
            p=m['parameters'];field=p.get('Inherited Field',3)
            if isinstance(field,bool) or field not in (0,2):
                raise ValueError('Parent update currently supports position and previous position only')
            # Reuse verified shared/default validation; the copy field is vector.
            Initializer({**p,'Inherited Field':3})
    return modules


class History:
    def __init__(self,operators,births,lifetimes,origins,velocities,parent_query,*,seed=0,step=1/120):
        if not math.isfinite(step) or step<=0:raise ValueError('Positive parent history step required')
        self.operators=operators;self.births=tuple(births);self.lifetimes=dict(lifetimes)
        self.origins={k:vector(v) for k,v in origins.items()}
        self.velocities={k:vector(v) for k,v in velocities.items()}
        self.parent_query=parent_query;self.step=step
        ids=[b.index for b in self.births]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate child birth identity')
        for b in self.births:
            if b.index not in self.origins or b.index not in self.velocities or b.index not in self.lifetimes:
                raise ValueError('Missing parent-update child birth inputs')
            if not math.isfinite(b.simulation_time) or b.simulation_time<0 or not math.isfinite(self.lifetimes[b.index]) or self.lifetimes[b.index]<=0:
                raise ValueError('Invalid child birth/lifetime')
        self.copy_indices=[i for i,m in enumerate(operators) if m['function']==NAME]
        state={b.index:self.initial(b) for b in self.births if b.simulation_time<=0}
        self.samples=[(state,{i:0 for i in self.copy_indices},random.Random(seed).getstate())]
        self.entries=len(state)

    def initial(self,b):
        current=tuple(f32(x) for x in self.origins[b.index])
        previous=tuple(f32(x-v*self.step) for x,v in zip(current,self.velocities[b.index]))
        return current,previous,self.step

    def advance(self,stored,clock,following):
        incoming,cursors,rngstate=stored
        cursors=dict(cursors);rng=random.Random();rng.setstate(rngstate)
        active=[b for b in self.births if b.simulation_time<=following<b.simulation_time+self.lifetimes[b.index]]
        states={b.index:incoming.get(b.index,self.initial(b)) for b in active}
        parent=None
        if active:parent=self.parent_query(following,following-clock)
        for index,module in enumerate(self.operators):
            name=module['function'];p=module['parameters']
            if name=='Movement Basic':
                for b in active:
                    current,previous,prior=states[b.index]
                    dt=following-max(clock,b.simulation_time)
                    if dt>0:
                        current,previous=movement(current,previous,vector(p.get('gravity',(0,0,0))),dt,prior,float(p.get('drag',0)))
                        states[b.index]=(current,previous,dt)
            elif name==NAME and parent is not None and parent.current:
                values=parent.current if p['Inherited Field']==0 else parent.previous
                cursor=cursors[index];count=len(values);scale=f32(float(p.get('Scale',1)))
                for b in active:
                    chosen=(math.trunc(f32(f32(count)*f32(rng.random()))) if p.get('Random Parent Particle Distribution',False)
                            else 0 if cursor>count-1 else cursor)
                    if not 0<=chosen<count:raise ValueError('Parent update selection outside buffer')
                    value=tuple(f32(f32(x)*scale) for x in values[chosen])
                    current,previous,prior=states[b.index]
                    states[b.index]=(value,previous,prior) if p['Inherited Field']==0 else (current,value,prior)
                    cursor=chosen+p.get('Particle Increment Amount',1)
                    if cursor>0x7fffffff:raise ValueError('Parent update cursor overflow')
                cursors[index]=cursor
        return states,cursors,rng.getstate()

    def query(self,clock):
        if not math.isfinite(clock) or clock<0:raise ValueError('Nonnegative parent update clock required')
        tick=round(clock/self.step)
        if abs(clock/self.step-tick)<1e-9:clock=tick*self.step
        target=math.floor(clock/self.step)
        if target>100000:raise ValueError('Parent update history tick limit exceeded')
        while len(self.samples)<=target:
            n=len(self.samples)
            sample=self.advance(self.samples[-1],(n-1)*self.step,n*self.step)
            self.entries+=len(sample[0])
            if self.entries>2000000:raise ValueError('Parent update history memory limit exceeded')
            self.samples.append(sample)
        result=self.samples[target]
        if clock>target*self.step:result=self.advance(result,target*self.step,clock)
        return dict(result[0])

    def position(self,birth,age):
        values=self.query(birth.simulation_time+age)
        if birth.index not in values:raise ValueError('Child not alive at parent update query')
        return values[birth.index][0]
