"""Separate Source yaw attribute (field 12, radians) and authored birth writes.

Installed yaw-flip adds pi after a remainder by float32 pi. RNG streams and
the random-angle setup's floating point rounding remain approximate.
"""
import math
import struct

PI32 = struct.unpack('<f', struct.pack('<f', math.pi))[0]


def parameters(p):
    values = {key: float(p.get(key, default)) for key, default in
              (('yaw_initial', 0), ('yaw_offset_min', 0),
               ('yaw_offset_max', 360), ('yaw_random_exponent', 1))}
    if not all(math.isfinite(v) for v in values.values()) or values['yaw_random_exponent'] <= 0:
        raise ValueError('Invalid Rotation Yaw Random bounds or exponent')
    if any(float(p.get(k, 0)) != 0 for k in ('operator start fadein', 'operator end fadein',
            'operator start fadeout', 'operator end fadeout', 'operator fade oscillate')):
        raise ValueError('Rotation Yaw Random strength timing is unsupported')
    if any(float(p.get(k, 1)) != 1 for k in ('operator time scale min', 'operator time scale max',
            'operator strength random scale min', 'operator strength random scale max')):
        raise ValueError('Rotation Yaw Random time/strength scaling is unsupported')
    if not p.get('run for killed parent particles', True):
        raise ValueError('Rotation Yaw Random killed-parent policy is unsupported')
    return values


def random_angle(p, rng):
    from particle_distribution import random_float_exp
    p = parameters(p)
    value = math.radians(p['yaw_initial'] + random_float_exp(
        rng, p['yaw_offset_min'], p['yaw_offset_max'], p['yaw_random_exponent']))
    if not math.isfinite(value):
        raise ValueError('Invalid particle yaw angle')
    return value


def flip(value):
    if not math.isfinite(value):
        raise ValueError('Invalid particle yaw angle')
    result = math.fmod(value, PI32) + math.pi
    return struct.unpack('<f', struct.pack('<f', result))[0]


def sample(modules, rng):
    from particle_sprite_state import sample_yaw_flip
    yaw, flipped = 0., False
    for module in modules:
        p = module['parameters']
        if not p.get('operator enabled', True):
            continue
        if module['function'] == 'Rotation Yaw Random':
            yaw = random_angle(p, rng)
        elif module['function'] == 'Rotation Yaw Flip Random':
            flipped = sample_yaw_flip(p, rng)
            if flipped:
                yaw = flip(yaw)
    return yaw, flipped


def value(definition,state,age,lifetime):
    """Evaluate yaw ramps independently; SpriteCard consumes this in radians."""
    modules=definition['modules']['operators']
    if not any(m['function']=='Ramp Scalar Linear Random' and m['parameters'].get('ramp field',3)==12
               and m['parameters'].get('operator enabled',True) for m in modules):
        return state.get('yaw',0.)
    if '_yaw_ramp_history' not in state:
        from particle_roll_history import History
        samples=state.get('scalar_oscillations',{})
        sampled=[{**m,'parameters':samples.get(i,m['parameters'])} for i,m in enumerate(modules)]
        state['_yaw_ramp_history']=History(sampled,state.get('yaw',0.),lifetime,field=12)
    return state['_yaw_ramp_history'].query(age)
