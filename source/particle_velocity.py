"""Authored random velocity ranges; Source RNG and initializer order unverified."""
import math

def settings(parameters):
    """Installed Velocity Random unpack table, factory getter 0x10233230.

    Registration 0x10388160/70 points to builder 0x1020b050. These defaults
    do not establish Source RNG or simulation tick parity.
    """
    return {'random_speed_min':0.,'random_speed_max':0.,
            'speed_in_local_coordinate_system_min':(0.,0.,0.),
            'speed_in_local_coordinate_system_max':(0.,0.,0.),
            'control_point_number':0,**parameters}

def validate(parameters):
    parameters=settings(parameters)
    if any(float(parameters.get(key,0))!=0 for key in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')):
        raise ValueError('Velocity Random initializer strength timing is unsupported')
    speeds=[float(parameters[k]) for k in ('random_speed_min','random_speed_max')]
    vectors=[parameters[k] for k in ('speed_in_local_coordinate_system_min','speed_in_local_coordinate_system_max')]
    if not all(math.isfinite(v) for v in speeds) or any(len(v)!=3 or not all(math.isfinite(float(c)) for c in v) for v in vectors):raise ValueError('Invalid random particle velocity bounds')
    cp=float(parameters.get('control_point_number',0))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:raise ValueError('Invalid particle velocity control point')
    return int(cp)

def sample(parameters,rng):
    parameters=settings(parameters)
    validate(parameters)
    speed=rng.uniform(float(parameters['random_speed_min']),float(parameters['random_speed_max']))
    z=rng.uniform(-1,1);angle=rng.uniform(0,math.tau)
    radial=math.sqrt(max(0.,1-z*z))
    world=(speed*radial*math.cos(angle),speed*radial*math.sin(angle),speed*z)
    local=tuple(rng.uniform(float(a),float(b)) for a,b in zip(parameters['speed_in_local_coordinate_system_min'],parameters['speed_in_local_coordinate_system_max']))
    return world,local
