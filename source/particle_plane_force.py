"""Installed plane-distance force arithmetic; not yet wired into simulation.

Static functions 0x101fde20 and 0x1037f7d0. CP position is world-space;
authored plane normal is used directly without rotation or normalization.
Python arithmetic differs from Source SIMD rounding and simulation history.
"""
import math

def settings(parameters):
    p={'Min distance from plane':0.,'Force at Min distance':(0.,0.,0.),
       'Max Distance from plane':1.,'Force at Max distance':(0.,0.,0.),
       'Plane Normal':(0.,0.,1.),'Control point number':0,'Exponent':1.,**parameters}
    for key in ('Force at Min distance','Force at Max distance','Plane Normal'):
        v=tuple(map(float,p[key]))
        if len(v)!=3 or not all(math.isfinite(x) for x in v):raise ValueError('Invalid plane-force vector')
        p[key]=v
    for key in ('Min distance from plane','Max Distance from plane','Exponent'):
        p[key]=float(p[key])
        if not math.isfinite(p[key]):raise ValueError('Nonfinite plane-force scalar')
    if not 0<=p['Exponent']<=1000:raise ValueError('Negative or excessive plane-force exponent is unverified')
    cp=float(p['Control point number'])
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:raise ValueError('Invalid plane-force control point')
    p['Control point number']=int(cp)
    return p

def acceleration(position,control_origin,parameters):
    p=settings(parameters)
    return acceleration_prepared(position,control_origin,p)

def acceleration_prepared(position,control_origin,p):
    """Evaluate already validated settings for a simulation step."""
    position=tuple(map(float,position));origin=tuple(map(float,control_origin))
    if len(position)!=3 or len(origin)!=3 or not all(math.isfinite(x) for x in position+origin):
        raise ValueError('Invalid plane-force position')
    distance=sum((a-b)*n for a,b,n in zip(position,origin,p['Plane Normal']))
    width=p['Max Distance from plane']-p['Min distance from plane']
    amount=(distance-p['Min distance from plane'])/width if width else 0.
    amount=max(0.,min(1.,amount))
    amount=amount**(math.trunc(p['Exponent']*4)/4)
    return tuple(a+(b-a)*amount for a,b in zip(p['Force at Min distance'],p['Force at Max distance']))
