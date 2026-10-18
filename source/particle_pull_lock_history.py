"""Experimental translation-lock history used by the converter's opt-in path.

Uses the existing ordered movement equation and shifts both position buffers
at the authored lock. Source lock buffer writes and tick phase need comparison.
"""
import math
from particle_vector_history import advance, vector
from particle_scalar_oscillation import f32


def snap_age(age,step):
    nearest=round(age/step)
    return nearest*step if abs(age/step-nearest)<1e-10 else age


def advance_step(operators,position,previous,color,clock,following,lifetime,prior_dt,
                 lock_delta,spatial_acceleration=None,acceleration=None):
    dt=following-clock
    for operator in operators:
        if not operator['parameters'].get('operator enabled',True):continue
        if operator['function']=='Movement Lock to Control Point':
            change=vector(lock_delta(operator['parameters'],clock,following,lifetime))
            position=tuple(f32(x+d) for x,d in zip(position,change))
            previous=tuple(f32(x+d) for x,d in zip(previous,change))
        else:
            position,previous,color=advance([operator],position,previous,color,(1.,1.,1.),
                following,lifetime,dt,prior_dt,acceleration=acceleration,
                spatial_acceleration=spatial_acceleration)
    return position,previous,color


def evaluate(operators, position, velocity, age, lifetime, lock_delta,
             spatial_acceleration=None, acceleration=None, step=1/120):
    if not all(math.isfinite(v) for v in (age,lifetime,step)) or age<0 or lifetime<=0 or step<=0:
        raise ValueError('Invalid lock history interval')
    age=snap_age(age,step)
    ticks=round(age/step) if abs(age/step-round(age/step))<1e-10 else math.ceil(age/step)
    if ticks>100000:raise ValueError('Lock history limit exceeded')
    position=vector(position)
    previous=tuple(x-v*step for x,v in zip(position,vector(velocity)))
    color=(1.,1.,1.);prior_dt=step;clock=0.
    for index in range(ticks):
        following=min(age,(index+1)*step);dt=following-clock
        position,previous,color=advance_step(operators,position,previous,color,clock,following,
            lifetime,prior_dt,lock_delta,spatial_acceleration,acceleration)
        clock=following;prior_dt=dt
    return position,previous


class History:
    """Retain eight full ticks; fractional queries never mutate stored ticks."""
    def __init__(self,operators,position,velocity,lifetime,lock_delta,
                 spatial_acceleration=None,acceleration=None,step=1/120):
        from collections import deque
        if not all(math.isfinite(v) for v in (lifetime,step)) or lifetime<=0 or step<=0:
            raise ValueError('Invalid history lifetime/timestep')
        self.operators=operators;self.position=vector(position);self.velocity=vector(velocity)
        self.lifetime=lifetime;self.lock=lock_delta;self.spatial=spatial_acceleration
        self.acceleration=acceleration;self.step=step
        previous=tuple(x-v*step for x,v in zip(self.position,self.velocity))
        self.samples=deque([(0,(self.position,previous,(1.,1.,1.)))],maxlen=8)
    def query(self,age):
        if not math.isfinite(age) or age<0 or math.ceil(age/self.step)>100000:
            raise ValueError('Invalid history query age')
        age=snap_age(age,self.step)
        target=round(age/self.step) if abs(age/self.step-round(age/self.step))<1e-10 else math.floor(age/self.step)
        if target<self.samples[0][0]:
            return evaluate(self.operators,self.position,self.velocity,age,self.lifetime,
                self.lock,self.spatial,self.acceleration,self.step)
        while self.samples[-1][0]<target:
            tick,state=self.samples[-1];clock=tick*self.step;following=(tick+1)*self.step
            prior=self.step if tick==0 else clock-(tick-1)*self.step
            state=advance_step(self.operators,*state,clock,following,self.lifetime,prior,
                self.lock,self.spatial,self.acceleration)
            self.samples.append((tick+1,state))
        tick,state=next(v for v in self.samples if v[0]==target);clock=tick*self.step
        if age>clock:
            prior=self.step if tick==0 else clock-(tick-1)*self.step
            state=advance_step(self.operators,*state,clock,age,self.lifetime,prior,
                self.lock,self.spatial,self.acceleration)
        return state[:2]


def bind_translation_delta(parameters, position_at_age, fade=(1.,1.)):
    """Prepare per-step translation in the same units as motion buffers.

    Uses the established experimental fade-lock weighting. Rotation, distance
    fades and nondefault shared strength/timing remain unsupported.
    """
    from particle_partial_lock import validate, displacement
    validate(parameters)
    from particle_pull_settings import settings
    shared={key:value for key,value in parameters.items() if key.startswith('operator ')}
    if settings(shared)['prototype_unsupported_features']:
        raise ValueError('Shared lock timing/strength requires ordered evaluation')
    threshold=float(parameters.get('instant jump threshold',512.))
    def delta(_parameters, start, end, lifetime):
        return displacement([(start,vector(position_at_age(start))),
                             (end,vector(position_at_age(end)))],
                            lifetime,*fade,instant_jump_threshold=threshold)
    return delta


def baked_position(definition,state,age,lifetime,scale,origin,target_at_clock):
    """Development bridge; returns world displacement in Blender units."""
    cached=state.get('_pull_lock_history')
    if cached is not None:
        return tuple(v*scale for v in cached.query(age)[0])
    from particle_spatial_force_context import bind
    from particle_random_force_history import history
    operators=[]
    locks=[]
    for index,module in enumerate(definition['modules']['operators']):
        if not module['parameters'].get('operator enabled',True):continue
        if module['function'] not in ('Movement Basic','Movement Lock to Control Point','Oscillate Vector'):continue
        parameters=module['parameters']
        if module['function']=='Oscillate Vector':parameters=state['vector_oscillations'][index]
        operators.append({'function':module['function'],'parameters':parameters})
        if module['function']=='Movement Lock to Control Point':locks.append(parameters)
    if len(locks)!=1:raise ValueError('Development pull-lock requires one translation lock')
    lock=locks[0]
    from particle_partial_lock import sampled_fades
    fade=state.get('translation_lock_fade')
    if fade is None:
        if sampled_fades(lock,.5,.5)!=(1.,1.):
            raise ValueError('Development pull-lock attachment fade requires a per-birth sample')
        fade=(1.,1.)
    clock=state['creation_simulation_time'];cp=int(lock.get('control_point_number',0))
    delta=bind_translation_delta(lock,lambda t:tuple(v/scale for v in target_at_clock(cp,clock+t)),fade=fade)
    force=bind(definition['modules']['forces'],origin,scale,clock,target_at_clock)
    # Ordered engine equations below use Source-unit buffers.
    spatial=lambda t,p:tuple(v/scale for v in force(t,tuple(v*scale for v in p)))
    random=history(definition['modules']['forces'],state['force_seed'])
    cached=History(operators,tuple(v/scale for v in state['offset']),
        tuple(v/scale for v in state['velocity']),lifetime,delta,
        spatial_acceleration=spatial,acceleration=random)
    state['_pull_lock_history']=cached
    return tuple(v*scale for v in cached.query(age)[0])
