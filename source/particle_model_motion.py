"""Ordered model-attached position updates with explicit evaluated model inputs.

Coordinates and gravity must use the same units. Model query clocks and shared
operator strength belong to the caller; this does not resolve scene bindings.
"""
import math
from particle_vector_history import movement,vector
from particle_bone_lock import apply

def advance(operators,position,previous,*,age,step,previous_step,target_pair,
            bypass=False,strength=1.):
    position,previous=vector(position),vector(previous)
    for operator in operators:
        p=operator['parameters']
        if not p.get('operator enabled',True):continue
        name=operator['function']
        if name=='Movement Basic':
            position,previous=movement(position,previous,vector(p.get('gravity',(0,0,0))),
                                       step,previous_step,float(p.get('drag',0)))
        elif name=='Movement Lock to Bone':
            old,new=target_pair(operator)
            position,previous=apply(position,previous,old,new,age=age,step=step,
                                    start=float(p.get('lifetime fade start',0)),
                                    end=float(p.get('lifetime fade end',0)),strength=strength,
                                    bypass=bypass,rigid=bool(p.get('rigid lock',False)))
        elif name=='Movement Lerp to Hitbox':
            from particle_hitbox_lerp import apply as lerp
            old,new=target_pair(operator)
            position,previous=lerp(position,previous,new,age=age,
                                   start=float(p.get('lifetime lerp start',0)),
                                   end=float(p.get('lifetime lerp end',1)),strength=strength)
        else:raise ValueError('Uninvestigated ordered model motion: '+name)
    return position,previous

class History:
    """Immutable full-tick snapshots with caller-owned animated target queries.

    Partial queries interpolate saved states and never apply movement twice.
    The 120 Hz clock and interpolation are converter approximations.
    """
    def __init__(self,operators,position,velocity,target_pair,*,step=1/120,
                 maximum_age,bypass_at=None):
        if not all(math.isfinite(v) for v in (step,maximum_age)) or step<=0 or maximum_age<0:
            raise ValueError('Finite positive step and nonnegative history limit required')
        import copy
        from particle_model_history import History as Snapshots
        from particle_hitbox_lerp import f32
        self.operators=copy.deepcopy(operators);self.target_pair=target_pair
        self.step=step;self.maximum_age=maximum_age;self.bypass_at=bypass_at
        self.snapshots=Snapshots()
        current=tuple(f32(v) for v in vector(position))
        previous=tuple(f32(x-v*step) for x,v in zip(current,vector(velocity)))
        self.snapshots.record(0.,current,previous)
    def query(self,age):
        if not math.isfinite(age) or not 0<=age<=self.maximum_age:
            raise ValueError('Query outside model motion history limit')
        while self.snapshots.times[-1]<age:
            prior=self.snapshots.times[-1]
            tick=math.floor(prior/self.step+1e-8)+1
            time=min(tick*self.step,self.maximum_age)
            if tick>1000000 or time<=prior:raise ValueError('Model motion history limit exceeded')
            current,previous=self.snapshots.snapshots[-1]
            previous_step=self.step if len(self.snapshots.times)==1 else prior-self.snapshots.times[-2]
            result=advance(self.operators,current,previous,age=time,step=time-prior,
                           previous_step=previous_step,
                           target_pair=lambda operator:self.target_pair(operator,prior,time),
                           bypass=self.bypass_at(prior,time) if self.bypass_at else False)
            self.snapshots.record(time,*result)
        return self.snapshots.query(age)
