"""Epitrochoid position arithmetic from installed initializer 0x10205320.

Shared scales are inactive when their corresponding seeds are zero.
Python trig replaces Source's table approximation; floating point differs.
"""
import math

def validate(parameters):
    for key,default in (('operator strength random scale min',1.),
                        ('operator strength random scale max',1.),
                        ('operator time scale min',1.),('operator time scale max',1.)):
        if not math.isfinite(float(parameters.get(key,default))):
            raise ValueError('Nonfinite epitrochoid shared scale')
    # Installed shared gate 0x101ebe20 only samples scale ranges when the
    # corresponding seed is nonzero. It does not rescale birth coordinates.
    for key in ('operator time scale seed','operator strength scale seed','operator time offset seed'):
        if float(parameters.get(key,0))!=0:
            raise ValueError('Epitrochoid seeded shared timing/strength is unverified')
    for key in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate'):
        if float(parameters.get(key,0))!=0:
            raise ValueError('Epitrochoid shared strength fades are unverified')
    for key in ('operator strength scale control point','operator end cap state'):
        if float(parameters.get(key,-1))!=-1:
            raise ValueError('Epitrochoid shared control-point/end-cap gate is unverified')
    if parameters.get('use particle count instead of creation time',False):
        raise ValueError('Epitrochoid context counter resets are unverified')
    if parameters.get('offset from existing position',False):
        raise ValueError('Epitrochoid existing-position composition is unverified')
    cp=float(parameters.get('control point number',0))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:
        raise ValueError('Invalid epitrochoid control point')
    offset(0,0,parameters)
    return int(cp)

def offset(creation_time, counter, parameters):
    p={'first dimension':0,'second dimension':1,'particle density':10.,
       'point offset':4.,'radius 1':40.,'radius 2':24.,
       'use particle count instead of creation time':False,**parameters}
    # CP scale overrides and existing-position composition are handled elsewhere.
    if p.get('scale from conrol point (radius 1/radius 2/offset)',-1)!=-1:
        raise ValueError('Epitrochoid control-point scaling is not validated')
    if isinstance(counter,bool) or not isinstance(counter,int) or counter<0:
        raise ValueError('Invalid epitrochoid counter')
    values=[float(p[k]) for k in ('particle density','point offset','radius 1','radius 2')]
    if not all(math.isfinite(v) for v in values+[float(creation_time)]):
        raise ValueError('Nonfinite epitrochoid parameters')
    density,distance,r1,r2=values
    total=r1+r2;denominator=r2+2**-23
    if total==0 or denominator==0:raise ValueError('Degenerate epitrochoid radii')
    phase=(counter if p['use particle count instead of creation time'] else float(creation_time))*density
    secondary=phase*total/denominator
    result=[0.,0.,0.]
    for key,trig in (('first dimension',math.cos),('second dimension',math.sin)):
        dimension=float(p[key])
        if not math.isfinite(dimension) or dimension!=int(dimension) or not -1<=dimension<=2:
            raise ValueError('Invalid epitrochoid dimension')
        if dimension!=-1:result[int(dimension)]=total*trig(phase)+distance*trig(secondary)
    return tuple(result)
