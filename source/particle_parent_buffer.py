"""Immutable parent simulation-buffer snapshots, independent of rendering.

The simulator supplies Source order and the current/previous positions for
every entry. No sorting, death compaction or timestep reconstruction is guessed.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Snapshot:
    instance_id: int
    time: float
    particle_ids: tuple
    current: tuple
    previous: tuple

    @classmethod
    def capture(cls,instance_id,time,particle_ids,current,previous):
        ids=tuple(particle_ids)
        current=tuple(tuple(float(v) for v in p) for p in current)
        previous=tuple(tuple(float(v) for v in p) for p in previous)
        if not isinstance(instance_id,int) or isinstance(instance_id,bool):
            raise ValueError('Integer parent instance identity required')
        if not math.isfinite(float(time)):raise ValueError('Finite parent buffer time required')
        if len(ids)!=len(current) or len(ids)!=len(previous):
            raise ValueError('Parent identity and position buffers must match')
        if len(set(ids))!=len(ids):raise ValueError('Parent buffer particle identities must be unique')
        if any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in (*current,*previous)):
            raise ValueError('Finite three-component parent buffer entries required')
        return cls(instance_id,float(time),ids,current,previous)

    def sample(self,index,fraction,inherited_scale=0):
        from particle_parent_sample import buffer_position
        return buffer_position(self.current,self.previous,index,fraction,inherited_scale)
