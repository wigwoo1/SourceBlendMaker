"""Prototype adapter for production's approximate 60 Hz random-force stream.

Does not implement Source RNG or engine force semantics.
"""
import math,random
from particle_pull_integrator import vec

def history(modules,seed):
    streams=[]
    for index,module in enumerate(modules):
        parameters=module['parameters']
        if module['function']!='random force' or not parameters.get('operator enabled',True):continue
        low=vec(parameters.get('min force',(0,0,0)));high=vec(parameters.get('max force',(0,0,0)))
        streams.append((random.Random(str(seed)+':'+str(index)),low,high,[]))
    def acceleration(age):
        age=float(age)
        if not math.isfinite(age) or age<0:raise ValueError('Invalid force age')
        # Snap arithmetic noise at a known 60 Hz boundary to the new tick.
        ticks=age*60;nearest=round(ticks)
        if abs(ticks-nearest)<1e-10:ticks=float(nearest)
        tick=math.floor(ticks)
        if tick>100000:raise ValueError('Random force history exceeds prototype limit')
        result=[0.,0.,0.]
        for rng,low,high,samples in streams:
            while len(samples)<=tick:
                samples.append(tuple(rng.uniform(a,b) for a,b in zip(low,high)))
            for axis in range(3):result[axis]+=samples[tick][axis]
        return vec(result)
    return acceleration
