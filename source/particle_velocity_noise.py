"""Installed Velocity Noise arithmetic, in Source units before scene scaling.

Three correlated spatial/time noise channels, not random vector samples.
The bake uses the returned physical velocity; Source timestep/position-buffer
rounding and engine tick parity remain approximate. CP rotation is supplied
by the scene adapter at particle creation time.
"""
import math
from particle_noise import f32, noise

PHASES = ((0., 0., 0.), (100000.5, 300000.25, 9000001.),
          (110000.25, 310000.75, 9100000.))


def _finite(value):
    try:
        result = f32(float(value))
    except (TypeError, ValueError, OverflowError):
        raise ValueError('Velocity Noise requires finite float32 values') from None
    if not math.isfinite(result):
        raise ValueError('Velocity Noise requires finite float32 values')
    return result


def _vector(value):
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError('Velocity Noise requires three-component vectors')
    return tuple(_finite(v) for v in value)


def settings(p):
    try:
        cp = float(p.get('Control Point Number', 0))
    except (TypeError, ValueError):
        raise ValueError('Invalid Velocity Noise control point') from None
    if not math.isfinite(cp) or cp != int(cp) or not 0 <= cp < 64:
        raise ValueError('Invalid Velocity Noise control point')
    result = {'Control Point Number': int(cp),
              'Apply Velocity in Local Space (0/1)': bool(_finite(p.get('Apply Velocity in Local Space (0/1)', 0)))}
    for name, default in (('Time Noise Coordinate Scale', 1),
                          ('Spatial Noise Coordinate Scale', .01), ('Time Coordinate Offset', 0)):
        result[name] = _finite(p.get(name, default))
    for name, default in (('Spatial Coordinate Offset', (0, 0, 0)),
                          ('Absolute Value', (0, 0, 0)), ('Invert Abs Value', (0, 0, 0)),
                          ('output minimum', (0, 0, 0)), ('output maximum', (1, 1, 1))):
        result[name] = _vector(p.get(name, default))
    return result


def sample(parameters, position, creation_time, tables=None, rotation=None, time_step=1.):
    """Return velocity (or a timestep-scaled delta for arithmetic validation).

Rotation is a 3x3 local-to-world matrix, not a translated CP transform.
Flags are independent: inversion does not implicitly enable absolute value.
Authored descending ranges are preserved and output is not clamped.
"""
    p = settings(parameters)
    position, creation_time, time_step = _vector(position), _finite(creation_time), _finite(time_step)
    if time_step < 0:
        raise ValueError('Velocity Noise timestep must be nonnegative')
    if tables is None:
        from particle_noise_emitter import tables as installed_tables
        tables = installed_tables()
    try:
        temporal = _finite(f32(creation_time + p['Time Coordinate Offset']) * p['Time Noise Coordinate Scale'])
        point = tuple(_finite(f32(f32(v + o) * p['Spatial Noise Coordinate Scale']) + temporal)
                      for v, o in zip(position, p['Spatial Coordinate Offset']))
        values = []
        for axis, phase in enumerate(PHASES):
            value = noise(tuple(_finite(a + b) for a, b in zip(point, phase)), tables)
            absolute = bool(p['Absolute Value'][axis])
            if absolute:
                value = abs(value)
            if p['Invert Abs Value'][axis]:
                value = f32(1 - value)
            half = 1. if absolute else .5
            low, high = p['output minimum'][axis], p['output maximum'][axis]
            span = _finite(high - low)
            bias = _finite(f32((1 - half) * span) + low)
            values.append(_finite(f32(f32(value * f32(span * half)) + bias) * time_step))
        if p['Apply Velocity in Local Space (0/1)']:
            if rotation is None or len(rotation) != 3:
                raise ValueError('Local Velocity Noise requires the birth control-point rotation')
            rows = tuple(_vector(row) for row in rotation)
            x, y, z = values
            # Installed VectorRotate sums Y, X, Z in that order.
            values = [_finite(f32(f32(y * row[1]) + f32(x * row[0])) + f32(z * row[2])) for row in rows]
    except OverflowError:
        raise ValueError('Velocity Noise arithmetic exceeds float32 range') from None
    return tuple(values)
