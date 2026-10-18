"""Deterministic offline random-force approximation at 60 samples/second.

Source RNG, engine tick rate and per-tick force correlation are not reproduced.
"""
import math
import random


def displacement(modules,seed,age,drag=0):
    result=[0.,0.,0.]
    age=max(0.,float(age));drag=max(0.,float(drag))
    def integral(t):
        if drag<=1e-8:return .5*t*t
        return t/drag+math.expm1(-drag*t)/(drag*drag)
    for index,module in enumerate(modules):
        p=module['parameters']
        if module['function']!='random force' or not p.get('operator enabled',True):continue
        rng=random.Random(str(seed)+':'+str(index))
        low=p.get('min force',[0,0,0]);high=p.get('max force',[0,0,0])
        for tick in range(math.ceil(age*60)):
            start=tick/60;end=min(age,(tick+1)/60)
            weight=integral(age-start)-integral(age-end)
            for axis in range(3):result[axis]+=rng.uniform(float(low[axis]),float(high[axis]))*weight
    return result
