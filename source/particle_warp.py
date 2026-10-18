"""Source Position Modify Warp Random initializer (birth-time approximation)."""
import math


def settings(parameters):
    def vector(name, default):
        result = tuple(float(v) for v in parameters.get(name, default))
        if len(result) != 3 or not all(math.isfinite(v) for v in result):
            raise ValueError('Invalid particle warp vector: ' + name)
        return result

    minimum = vector('warp min', (1., 1., 1.))
    maximum = vector('warp max', (1., 1., 1.))
    duration = float(parameters.get('warp transition time (treats min/max as start/end sizes)', 0.))
    start = float(parameters.get('warp transition start time', 0.))
    control = float(parameters.get('control_point_number', 0))
    if not all(math.isfinite(v) for v in (duration, start, control)) or duration < 0 or control != int(control) or not 0 <= control < 64:
        raise ValueError('Invalid particle warp timing or control point')
    reverse = parameters.get('reverse warp (0/1)', parameters.get('reverse warp', parameters.get('reverse', False)))
    if reverse not in (False, True, 0, 1):
        raise ValueError('Invalid particle warp reverse flag')
    if reverse:
        minimum, maximum = maximum, minimum
    return {'minimum': minimum, 'maximum': maximum, 'duration': duration,
            'start': start, 'control_point': int(control),
            'random': duration == 0 and minimum != maximum}


def factor(parameters, creation_time, random_values=None):
    """Choose axis scale, interpolating over particle age when duration is set."""
    cfg = settings(parameters)
    time = float(creation_time)
    if not math.isfinite(time):
        raise ValueError('Invalid particle warp creation time')
    if cfg['random']:
        if random_values is None:
            raise ValueError('Random particle warp requires three random values')
        values = tuple(float(v) for v in random_values)
        if len(values) != 3 or not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
            raise ValueError('Invalid particle warp random values')
        return tuple(a + (b-a)*v for a,b,v in zip(cfg['minimum'],cfg['maximum'],values))
    if cfg['duration'] == 0:
        return cfg['minimum']
    amount = min(1., max(0., (time-cfg['start'])/cfg['duration']))
    return tuple(a + (b-a)*amount for a,b in zip(cfg['minimum'],cfg['maximum']))


def _rotate(rotation, vector):
    return tuple(sum(float(rotation[row][column])*vector[column] for column in range(3)) for row in range(3))


def transform_position(position, origin, rotation, scale):
    """Apply the axis scale around a control point using its world transform."""
    local = _rotate(tuple(zip(*rotation)), tuple(float(position[i])-float(origin[i]) for i in range(3)))
    return tuple(float(origin[i])+value for i,value in enumerate(_rotate(rotation, tuple(local[i]*scale[i] for i in range(3)))))


def transform_vector(vector, rotation, scale):
    local = _rotate(tuple(zip(*rotation)), tuple(float(v) for v in vector))
    return _rotate(rotation, tuple(local[i]*scale[i] for i in range(3)))


def apply_birth(position, offset, velocity, modules, creation_time, control_query, rng):
    """Warp birth position, spawn offset and velocity in authored module order."""
    position = tuple(float(v) for v in position)
    offset = tuple(float(v) for v in offset)
    velocity = tuple(float(v) for v in velocity)
    for module in modules:
        if module['function'] != 'Position Modify Warp Random' or not module['parameters'].get('operator enabled', True):
            continue
        parameters = module['parameters']
        cfg = settings(parameters)
        random_values = tuple(rng.random() for _ in range(3)) if cfg['random'] else None
        scale = factor(parameters, creation_time, random_values)
        origin, rotation = control_query(cfg['control_point'])
        position = transform_position(position, origin, rotation, scale)
        offset = transform_vector(offset, rotation, scale)
        velocity = transform_vector(velocity, rotation, scale)
    return position, offset, velocity
