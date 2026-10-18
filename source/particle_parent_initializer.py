"""Position From Parent Particles birth operation on supplied buffer snapshots.

Source random-stream alignment, active-buffer compaction and killed-parent
dispatch remain unverified. A missing parent is an error; an existing empty
parent returns no birth, matching the inspected zero-active lifetime branch.
"""
import math
from particle_parent_sample import selection,birth_fraction


def motion(current,previous,timestep,scale):
    """Adapt parent position buffers to the converter's velocity convention.

    timestep must be the simulation tick, never the render frame duration.
    This conversion is approximate when the engine and converter tick differ.
    A zero tick can represent stationary buffers only.
    """
    if len(current)!=3 or len(previous)!=3:
        raise ValueError('Three-component inherited position buffers required')
    if not all(math.isfinite(float(v)) for v in (*current,*previous,timestep,scale)) or timestep<0 or scale<=0:
        raise ValueError('Finite inherited motion and positive world scale required')
    delta=tuple(float(a)-float(b) for a,b in zip(current,previous))
    if timestep==0 and any(delta):raise ValueError('Moving parent buffers require a simulation timestep')
    origin=tuple(float(v)*scale for v in current)
    velocity=tuple(v*scale/timestep if timestep else 0. for v in delta)
    return origin,velocity


class Initializer:
    def __init__(self,parameters):
        defaults={'operator start fadein':0,'operator end fadein':0,'operator start fadeout':0,
                  'operator end fadeout':0,'operator fade oscillate':0,'operator time offset min':0,
                  'operator time offset max':0,'operator time scale min':1,'operator time scale max':1,
                  'operator strength random scale min':1,'operator strength random scale max':1,
                  'operator strength scale control point':-1,'operator end cap state':-1}
        if any(float(parameters.get(key,value))!=value for key,value in defaults.items()):
            raise ValueError('Parent initializer shared strength/time gates are unverified')
        self.random=bool(parameters.get('Random Parent Particle Distribution',False))
        self.increment=float(parameters.get('Particle Increment Amount',1))
        self.velocity_scale=float(parameters.get('Inherited Velocity Scale',0))
        if not math.isfinite(self.increment) or self.increment<0:
            raise ValueError('Negative or nonfinite parent increment remains unsupported')
        if not math.isfinite(self.velocity_scale):raise ValueError('Finite inherited parent velocity scale required')
        if not parameters.get('run for killed parent particles',True):
            raise ValueError('Killed-parent dispatch filtering requires collection scheduling')
        self.cursor=0.

    def initialize(self,snapshot,creation_time,timestep,random_value=None):
        if snapshot is None:raise ValueError('Parent particle simulation is missing')
        if not snapshot.current:return None
        if self.random and random_value is None:raise ValueError('Parent selection requires a random draw')
        index,following=selection(len(snapshot.current),self.cursor,self.increment,
            random_value if self.random else None)
        fraction=birth_fraction(creation_time,snapshot.time,timestep)
        current,previous=snapshot.sample(index,fraction,self.velocity_scale)
        self.cursor=following
        return current,previous
