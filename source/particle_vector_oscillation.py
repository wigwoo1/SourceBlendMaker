"""Recognize the installed zero-rate vector-position oscillation case.

Nonzero position/RGB oscillation is retained for ordered simulation history.
"""
import copy
import math


def resolve_zero_rate(definition):
    removed=[]
    for module in definition['modules']['operators']:
        if module['function']!='Oscillate Vector' or not module['parameters'].get('operator enabled',True):
            continue
        from particle_vector_history import settings
        p=settings(module['parameters'])
        if any(float(v)!=0 for key in ('oscillation rate min','oscillation rate max') for v in p[key]):
            continue
        for key in ('oscillation rate min','oscillation rate max'):
            rate=p.get(key,(0,0,0))
            if isinstance(rate,str):rate=rate.replace(',',' ').split()
            if len(rate)!=3 or any(float(v)!=0 for v in rate):
                raise ValueError('Nonzero vector oscillation requires per-tick simulation history')
        for key in ('oscillation frequency min','oscillation frequency max'):
            frequency=p.get(key,(1,1,1))
            if isinstance(frequency,str):frequency=frequency.replace(',',' ').split()
            if len(frequency)!=3 or not all(math.isfinite(float(v)) for v in frequency):
                raise ValueError('Nonfinite vector oscillation frequency')
        for key,default in (('oscillation multiplier',2),('oscillation start phase',.5)):
            if not math.isfinite(float(p.get(key,default))):raise ValueError('Nonfinite vector oscillation phase')
        removed.append(module)
    if not removed:return definition,False
    result=copy.deepcopy(definition)
    result['modules']['operators']=[m for i,m in enumerate(result['modules']['operators'])
        if definition['modules']['operators'][i] not in removed]
    return result,True
