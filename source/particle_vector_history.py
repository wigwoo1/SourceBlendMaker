"""Ordered vector oscillation and movement on an approximate birth clock.

Wave/defaults and position-buffer writes follow installed static evidence.
120 Hz birth clock, sampled converter RNG, drag power approximation and
birth-relative fade writes still need Source runtime comparison.
"""
import math
from collections import deque
from particle_scalar_oscillation import f32, wave

DEFAULTS = {'oscillation field': 0, 'offset instead of accelerate position': False,
            'oscillation rate min': (0., 0., 0.), 'oscillation rate max': (0., 0., 0.),
            'oscillation frequency min': (1., 1., 1.), 'oscillation frequency max': (1., 1., 1.),
            'proportional 0/1': True, 'start/end proportional': True,
            'start time min': 0., 'start time max': 0., 'end time min': 1., 'end time max': 1.,
            'oscillation multiplier': 2., 'oscillation start phase': .5}

def vector(value):
    if isinstance(value, str): value = value.replace(',', ' ').split()
    if len(value) != 3: raise ValueError('Expected three vector components')
    result = tuple(float(v) for v in value)
    if not all(math.isfinite(v) for v in result): raise ValueError('Nonfinite vector')
    return result

def settings(parameters):
    result = {**DEFAULTS, **parameters}
    if result['oscillation field'] not in (0, 6):
        raise ValueError('Only position and RGB fields currently investigated')
    for key in ('offset instead of accelerate position', 'proportional 0/1', 'start/end proportional'):
        if not isinstance(result[key], bool): raise ValueError('Invalid boolean clock/mode')
    for prefix in ('oscillation rate', 'oscillation frequency'):
        for suffix in (' min', ' max'): result[prefix + suffix] = vector(result[prefix + suffix])
        if any(a > b for a, b in zip(result[prefix + ' min'], result[prefix + ' max'])):
            raise ValueError('Reversed component range')
    for key in ('start time min', 'start time max', 'end time min', 'end time max',
                'oscillation multiplier', 'oscillation start phase'):
        if isinstance(result[key], bool): raise ValueError('Invalid numeric parameter')
        result[key] = float(result[key])
        if not math.isfinite(result[key]): raise ValueError('Nonfinite numeric parameter')
    if result['start time min'] > result['start time max'] or result['end time min'] > result['end time max']:
        raise ValueError('Reversed window range')
    return result

def sample(parameters, rng):
    p = settings(parameters)
    for prefix in ('oscillation frequency', 'oscillation rate'):
        result = tuple(a if a == b else rng.uniform(a, b)
                       for a, b in zip(p[prefix + ' min'], p[prefix + ' max']))
        p[prefix + ' min'] = p[prefix + ' max'] = result
    for prefix in ('start time', 'end time'):
        a, b = p[prefix + ' min'], p[prefix + ' max']
        p[prefix + ' min'] = p[prefix + ' max'] = a if a == b else rng.uniform(a, b)
    return p

def increment(p, age, lifetime, dt):
    for prefix in ('oscillation frequency', 'oscillation rate', 'start time', 'end time'):
        if p[prefix + ' min'] != p[prefix + ' max']: raise ValueError('Unsampled random range')
    if lifetime <= 0 or dt < 0 or age < 0: raise ValueError('Invalid simulation interval')
    clock = age / lifetime if p['start/end proportional'] else age
    if not p['start time min'] <= clock < p['end time min']: return (0., 0., 0.)
    result = []
    for frequency, rate in zip(p['oscillation frequency min'], p['oscillation rate min']):
        phase = age * frequency
        if p['proportional 0/1']:
            phase = phase / lifetime * p['oscillation multiplier'] + p['oscillation start phase']
        result.append(f32(wave(phase) * f32(rate * dt)))
    return tuple(result)

def movement(current, previous, acceleration, dt, previous_dt, drag=0.):
    """Installed buffer swap equation; transcendental drag remains approximate."""
    if dt <= 0 or previous_dt <= 0 or not 0 <= drag < 1:
        raise ValueError('Movement interval or drag outside investigated range')
    dt, previous_dt = f32(dt), f32(previous_dt)
    # Mirror the installed float32 boundaries around log/exp helpers. Python's
    # transcendental result may differ by a last bit from the installed tables.
    base = f32(1. - f32(drag))
    exponent = f32(f32(f32(math.log(base)) * 29.999998092651367) * dt)
    damping = f32(math.exp(exponent))
    coefficient = f32(f32(damping) * f32(dt / previous_dt))
    dt_squared = f32(dt * dt)
    result = tuple(f32(f32(f32(f32(x - old) * coefficient) + f32(a * dt_squared)) + x)
                   for x, old, a in zip(current, previous, acceleration))
    return result, tuple(current)

def evaluate(operators, initial_position, velocity, initial_color, age, lifetime,
             step=1/120, acceleration=None, spatial_acceleration=None):
    if not all(math.isfinite(v) for v in (age, lifetime, step)) or age < 0 or lifetime <= 0 or step <= 0:
        raise ValueError('Invalid history interval')
    ticks = math.floor(age / step)
    if ticks > 1000000: raise ValueError('History limit exceeded')
    position = tuple(f32(v) for v in vector(initial_position))
    previous = tuple(f32(x - v * step) for x, v in zip(position, vector(velocity)))
    color = tuple(f32(v) for v in vector(initial_color))
    prior_time = 0.; prior_dt = step
    times = [i * step for i in range(1, ticks + 1)]
    if not times or times[-1] < age: times.append(age)
    for time in times:
        dt = time - prior_time
        if dt == 0: continue
        position, previous, color = advance(operators, position, previous, color, initial_color,
                                            time, lifetime, dt, prior_dt, acceleration, spatial_acceleration)
        prior_time = time; prior_dt = dt
    return position, previous, color

def advance(operators, position, previous, color, initial_color, time, lifetime, dt, prior_dt,
            acceleration=None, spatial_acceleration=None):
    for operator in operators:
        p = operator['parameters']; name = operator['function']
        if not p.get('operator enabled', True): continue
        if name == 'Movement Basic':
            gravity = vector(p.get('gravity', (0., 0., 0.)))
            force = vector(acceleration(time) if acceleration else (0., 0., 0.))
            # Read the position at this authored movement operator, after any
            # preceding oscillators. A post-simulation displacement cannot
            # reproduce forces whose direction depends on particle position.
            spatial = vector(spatial_acceleration(time, position) if spatial_acceleration else (0., 0., 0.))
            force = tuple(a+b for a,b in zip(force, spatial))
            position, previous = movement(position, previous, tuple(g+a for g,a in zip(gravity, force)),
                                          dt, prior_dt, float(p.get('drag', 0.)))
        elif name == 'Oscillate Vector':
            change = increment(p, time, lifetime, dt)
            if p['oscillation field'] == 0:
                position = tuple(f32(x+change[i]) for i,x in enumerate(position))
                if p['offset instead of accelerate position']:
                    previous = tuple(f32(x+change[i]) for i,x in enumerate(previous))
            else: color = tuple(min(1.,max(0.,f32(c+change[i]))) for i,c in enumerate(color))
        elif name == 'Color Fade':
            from particle_color_fade import color as fade
            from particle_sprite_state import linear_color
            from particle_color_timing import active
            if active(p,p.get('_collection_birth',0.)+time):
                color = fade(initial_color, linear_color(p.get('color_fade',(255,)*4)), time/lifetime, p,current=color)
        else: raise ValueError('Uninvestigated ordered operator: ' + name)
    return position, previous, color

class History:
    """Keep eight complete ticks; partial queries never alter simulation history."""
    def __init__(self, operators, position, velocity, color, lifetime, step=1/120,
                 acceleration=None, spatial_acceleration=None):
        if not all(math.isfinite(v) for v in (lifetime,step)) or lifetime<=0 or step<=0:
            raise ValueError('Invalid history lifetime or timestep')
        self.operators=operators; self.position=vector(position); self.velocity=vector(velocity)
        self.color=vector(color); self.lifetime=lifetime; self.step=step; self.acceleration=acceleration
        self.spatial_acceleration=spatial_acceleration
        current=tuple(f32(x) for x in self.position)
        previous=tuple(f32(x-v*step) for x,v in zip(current,self.velocity))
        self.samples=deque([(0,(current,previous,tuple(f32(c) for c in self.color)))],maxlen=8)

    def query(self, age):
        if not math.isfinite(age) or age<0: raise ValueError('Invalid history age')
        target=math.floor(age/self.step)
        if target>1000000: raise ValueError('History limit exceeded')
        if target<self.samples[0][0]:
            return evaluate(self.operators,self.position,self.velocity,self.color,age,self.lifetime,
                            self.step,self.acceleration,self.spatial_acceleration)
        while self.samples[-1][0]<target:
            tick, state=self.samples[-1]; following=(tick+1)*self.step
            # Use the same double-precision tick differences as the reference.
            dt=following-tick*self.step
            prior_dt=self.step if tick==0 else tick*self.step-(tick-1)*self.step
            state=advance(self.operators,*state,self.color,following,self.lifetime,dt,prior_dt,
                          self.acceleration,self.spatial_acceleration)
            self.samples.append((tick+1,state))
        tick,state=next(s for s in self.samples if s[0]==target)
        base=tick*self.step
        if age>base:
            prior_dt=self.step if tick==0 else base-(tick-1)*self.step
            state=advance(self.operators,*state,self.color,age,self.lifetime,age-base,prior_dt,
                          self.acceleration,self.spatial_acceleration)
        return state
