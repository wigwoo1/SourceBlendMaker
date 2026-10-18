"""Bounded cache of the converter's existing piecewise random-force model.

Source RNG/tick fidelity is unchanged. Old queries use the original evaluator.
"""
import math,random
from collections import deque

class ForceHistory:
    def __init__(self,modules,seed,drag=0):
        self.modules=modules;self.seed=seed;self.drag=max(0.,float(drag))
        self.histories=[]
        for index,module in enumerate(modules):
            p=module['parameters']
            if module['function']!='random force' or not p.get('operator enabled',True):continue
            rng=random.Random(str(seed)+':'+str(index))
            low=p.get('min force',[0,0,0]);high=p.get('max force',[0,0,0])
            draw=lambda rng=rng,low=low,high=high:tuple(rng.uniform(float(a),float(b)) for a,b in zip(low,high))
            self.histories.append({'draw':draw,'tick':0,'samples':deque([(0,(0.,)*3,(0.,)*3,draw())],maxlen=8)})

    def advance(self,position,velocity,force,dt):
        if self.drag<=1e-8:
            return (tuple(x+v*dt+.5*a*dt*dt for x,v,a in zip(position,velocity,force)),
                    tuple(v+a*dt for v,a in zip(velocity,force)))
        loss=-math.expm1(-self.drag*dt)
        decay=1-loss;velocity_weight=loss/self.drag
        acceleration_weight=dt/self.drag-loss/(self.drag*self.drag)
        return (tuple(x+v*velocity_weight+a*acceleration_weight for x,v,a in zip(position,velocity,force)),
                tuple(v*decay+a*velocity_weight for v,a in zip(velocity,force)))

    def query(self,age):
        age=max(0.,float(age))
        if not math.isfinite(age):raise ValueError('Invalid force history age')
        # Small positive drag suffers cancellation in the incremental integral.
        # Preserve the existing evaluator's result in this ill-conditioned range.
        if 1e-8<self.drag<.01:
            from particle_forces import displacement
            return displacement(self.modules,self.seed,age,self.drag)
        target=math.floor(age*60)
        if any(target<h['samples'][0][0] for h in self.histories):
            from particle_forces import displacement
            return displacement(self.modules,self.seed,age,self.drag)
        result=[0.,0.,0.]
        for h in self.histories:
            while h['tick']<target:
                tick,position,velocity,force=h['samples'][-1]
                position,velocity=self.advance(position,velocity,force,1/60)
                h['tick']+=1
                h['samples'].append((h['tick'],position,velocity,h['draw']()))
            tick,position,velocity,force=next(s for s in h['samples'] if s[0]==target)
            position,_=self.advance(position,velocity,force,age-target/60)
            for axis in range(3):result[axis]+=position[axis]
        return result
