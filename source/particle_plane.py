"""Installed plane constraint, applied to sampled particle centers.

Projection arithmetic matches the decoded operation. Collision integration
between samples is approximate, especially for moving planes and forces.
"""
import math
from particle_ring import rotate

def settings(parameters):
    p={'control point number':0,'plane point':(0,0,0),'plane normal':(0,0,1),
       'global origin':False,'global normal':False,**parameters}
    for key in ('plane point','plane normal'):
        v=tuple(map(float,p[key]))
        if len(v)!=3 or not all(math.isfinite(c) for c in v):raise ValueError('Invalid particle '+key)
        p[key]=v
    if math.hypot(*p['plane normal'])==0:raise ValueError('Particle plane normal must be nonzero')
    cp=float(p['control point number'])
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:raise ValueError('Invalid plane control point')
    if any(float(p.get(k,0))!=0 for k in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')):
        raise ValueError('Plane constraint strength timing is unverified')
    return p

def world_plane(parameters,rotation,origin,scale):
    p=settings(parameters);scale=float(scale)
    if not math.isfinite(scale) or scale<=0:raise ValueError('Invalid plane unit scale')
    point=p['plane point'] if p['global origin'] else rotate(rotation,p['plane point'])
    point=tuple(v*scale for v in point)
    if not p['global origin']:point=tuple(a+b for a,b in zip(point,origin))
    normal=p['plane normal'] if p['global normal'] else rotate(rotation,p['plane normal'])
    length=math.hypot(*normal)
    return point,tuple(c/length for c in normal)

def project(center,radius,point,normal):
    center=tuple(map(float,center));radius=float(radius)
    if len(center)!=3 or not all(math.isfinite(v) for v in (*center,radius,*point,*normal)):raise ValueError('Invalid plane projection')
    penetration=sum((a-b)*n for a,b,n in zip(center,point,normal))-radius
    return tuple(c-n*min(0.,penetration) for c,n in zip(center,normal))
