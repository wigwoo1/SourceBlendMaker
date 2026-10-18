"""Offline 120 Hz midpoint integration for plane-distance forces.

Source tick scheduling, force RNG and shared operator timing remain unverified.
All inputs and CP callback positions are in Source units and simulation seconds.
"""
import math
from particle_plane_force import acceleration_prepared,settings

def simulate(position,velocity,age,forces,target,gravity=(0,0,0),drag=0,birth_clock=0):
    position=tuple(map(float,position));velocity=tuple(map(float,velocity));gravity=tuple(map(float,gravity))
    age=float(age);drag=float(drag)
    if any(len(v)!=3 for v in (position,velocity,gravity)) or not all(math.isfinite(v) for v in position+velocity+gravity+(age,drag,birth_clock)):
        raise ValueError('Invalid plane-force motion inputs')
    if age<0 or drag<0 or math.ceil(age*120)>100000:raise ValueError('Plane-force integration budget exceeded')
    parsed=[settings(p) for p in forces]
    def total(point,speed,t):
        result=[gravity[i]-drag*speed[i] for i in range(3)]
        for p in parsed:
            a=acceleration_prepared(point,target(p['Control point number'],birth_clock+t),p)
            for i in range(3):result[i]+=a[i]
        return result
    t=0.
    for tick in range(math.ceil(age*120)):
        dt=min(age,(tick+1)/120)-t
        a=total(position,velocity,t)
        midpoint=tuple(position[i]+velocity[i]*dt/2 for i in range(3))
        midspeed=tuple(velocity[i]+a[i]*dt/2 for i in range(3))
        middle_a=total(midpoint,midspeed,t+dt/2)
        position=tuple(position[i]+midspeed[i]*dt for i in range(3))
        velocity=tuple(velocity[i]+middle_a[i]*dt for i in range(3))
        t+=dt
    return position,velocity
