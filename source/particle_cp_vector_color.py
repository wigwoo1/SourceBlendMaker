"""Installed Remap Control Point to Vector RGB initializer (field 6).

Control points carry Source-unit component data. Resulting field values are
already linear RGB, not color bytes. Engine emission-batch timing is approximate.
"""
import math
from particle_scalar_oscillation import f32


def settings(p):
    field=float(p.get('output field',0))
    if field!=6:
        raise ValueError('Control-point vector initializer currently supports RGB field 6')
    cp=float(p.get('input control point number',0))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:
        raise ValueError('Invalid vector initializer input control point')
    if float(p.get('local space CP',-1))!=-1:
        raise ValueError('Control-point vector initializer local-space bounds require transform evaluation')
    defaults={'operator start fadein':0,'operator end fadein':0,'operator start fadeout':0,
              'operator end fadeout':0,'operator fade oscillate':0,'operator time offset min':0,
              'operator time offset max':0,'operator time scale min':1,'operator time scale max':1,
              'operator strength random scale min':1,'operator strength random scale max':1,
              'operator strength scale control point':-1,'operator end cap state':-1}
    if any(float(p.get(k,v))!=v for k,v in defaults.items()):
        raise ValueError('Control-point vector initializer shared strength/time gates are unverified')
    result={'control_point':int(cp),'multiply':bool(p.get('output is scalar of initial random range',False))}
    for name in ('input minimum','input maximum','output minimum','output maximum'):
        vector=p.get(name,(0.,0.,0.))
        if len(vector)!=3 or not all(math.isfinite(float(v)) for v in vector):
            raise ValueError('Finite three-component vector initializer bounds required')
        result[name]=tuple(f32(float(v)) for v in vector)
    for name in ('emitter lifetime start time (seconds)','emitter lifetime end time (seconds)'):
        value=float(p.get(name,-1))
        if not math.isfinite(value):raise ValueError('Finite vector initializer creation-time gate required')
        result[name]=f32(value)
    return result


def color(p, control_point, initial, creation_time):
    cfg=settings(p)
    if len(initial)!=3 or len(control_point)!=3 or not all(math.isfinite(float(v)) for v in list(initial)+list(control_point)+[creation_time]):
        raise ValueError('Finite RGB and control-point components required')
    start=cfg['emitter lifetime start time (seconds)']
    end=cfg['emitter lifetime end time (seconds)']
    # The installed scalar branch disables the whole gate when either bound
    # equals -1. Otherwise the creation-time interval is [start,end).
    time=f32(creation_time)
    if start!=-1 and end!=-1 and not start<=time<end:
        return tuple(initial)
    result=[]
    for value,lo,hi,a,b,old in zip(control_point,cfg['input minimum'],cfg['input maximum'],
                                 cfg['output minimum'],cfg['output maximum'],initial):
        value=f32(float(value))
        if lo==hi:
            mapped=b if value>=hi else a
        else:
            fraction=max(0.,min(1.,f32(f32(value-lo)/f32(hi-lo))))
            mapped=f32(a+f32(f32(b-a)*fraction))
        if cfg['multiply']:mapped=f32(mapped*f32(float(old)))
        result.append(max(0.,min(1.,mapped)))
    return tuple(result)


def initialize(modules, initial, creation_time, query):
    result=tuple(initial)
    for module in modules:
        if module['function']!='Remap Control Point to Vector' or not module['parameters'].get('operator enabled',True):
            continue
        cfg=settings(module['parameters'])
        if query is None:raise ValueError('Control-point RGB initializer requires an imported control-point query')
        result=color(module['parameters'],query(cfg['control_point']),result,creation_time)
    return result
