"""Validated settings for the pending kill-on-trace particle simulation.

Parsing settings does not enable collision baking. Scene collision geometry,
engine contents filtering, and persistent killed-particle history are required.
"""
import math


def settings(parameters):
    from particle_epitrochoid import validate as validate_shared
    try:
        validate_shared({k:v for k,v in parameters.items() if k.startswith('operator ')})
    except ValueError as exc:
        raise ValueError('Trace collision shared timing/strength is unsupported: '+str(exc)) from exc
    defaults={'collision mode':0,'amount of bounce':0.,'amount of slide':0.,
              'radius scale':1.,'brush only':False,'collision group':'NONE',
              'control point offset for fast collisions':(0.,0.,0.),
              'control point movement distance tolerance':5.,
              'kill particle on collision':False,'minimum speed to kill on collision':-1.,
              'Confirm Collision':False,'trace accuracy tolerance':24.}
    p={**defaults,**parameters}
    if float(p['collision mode'])!=0:raise ValueError('Only standard trace collision mode is prepared')
    if not p['kill particle on collision']:raise ValueError('Bounce/slide collision response is not prepared')
    if float(p['minimum speed to kill on collision'])!=-1:raise ValueError('Speed-gated collision killing is not prepared')
    if p['Confirm Collision']:raise ValueError('Confirmed secondary collision traces are not prepared')
    if str(p['collision group']).upper() not in ('NONE','DEBRIS'):
        raise ValueError('Collision group filtering is not prepared for this group')
    for key in ('amount of bounce','amount of slide','radius scale',
                'control point movement distance tolerance','trace accuracy tolerance'):
        value=float(p[key])
        if not math.isfinite(value) or value<0:raise ValueError('Invalid collision '+key)
        p[key]=value
    offset=p['control point offset for fast collisions']
    if isinstance(offset,str):offset=offset.replace(',',' ').split()
    if len(offset)!=3 or not all(math.isfinite(float(v)) for v in offset):
        raise ValueError('Invalid collision control-point offset')
    p['control point offset for fast collisions']=tuple(map(float,offset))
    p['collision group']=str(p['collision group']).upper()
    return p
