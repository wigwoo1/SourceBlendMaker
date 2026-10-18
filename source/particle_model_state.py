"""Persistent selected-hitbox state for an explicitly evaluated model binding.

The caller owns simulation times and operator order. The model scene adapter
uses this state during baking; Source tick and random-stream parity are unproven.
"""
from particle_model_selection import select
from particle_hitbox_lerp import apply
import math

class State:
    def __init__(self,binding,parameters,rng,depsgraph):
        self.binding=binding
        self.selection=select(parameters,len(binding.boxes),rng)
        self.point_policy={'allow_extrapolation':True} if any(v<0 or v>1 for v in self.selection['relative']) else {}
        self.position=binding.point(self.selection['index'],self.selection['relative'],depsgraph,**self.point_policy)
        self.previous_position=self.position
        self.last_age=0.
        self.last_update=None
    def lerp(self,age,depsgraph,parameters,*,strength=1.,target=None):
        if not math.isfinite(age):raise ValueError('Finite model particle age required')
        if age<self.last_age:raise ValueError('Model particle simulation must advance chronologically')
        signature=(float(parameters.get('lifetime lerp start',0)),float(parameters.get('lifetime lerp end',1)),float(strength))
        if self.last_update is not None and age==self.last_age:
            if signature!=self.last_update:raise ValueError('Repeated model particle time changed operator settings')
            return self.position
        if target is None:target=self.binding.point(self.selection['index'],self.selection['relative'],depsgraph,**self.point_policy)
        self.position,self.previous_position=apply(self.position,self.previous_position,target,age=age,
            start=float(parameters.get('lifetime lerp start',0)),end=float(parameters.get('lifetime lerp end',1)),strength=strength)
        self.last_age=age
        self.last_update=signature
        return self.position
