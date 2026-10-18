"""Birth noise mapping recovered from installed PET static instructions.

Used by the experimental noise birth adapter. World-time coordinates need the
engine's external clock and remain unsupported; Source tick/RNG parity is unverified.
Positions passed here are Source units, before Blender scene scaling.
"""
import math
from particle_noise import f32, noise


def sample(parameters, position, creation_time, tables):
    if float(parameters.get('world time noise coordinate scale', 0)) != 0:
        raise ValueError('World-time noise coordinates are unsupported')
    field = int(parameters.get('output field', 3))
    if field not in (1, 3, 4, 5, 7, 12, 16, 20):
        raise ValueError('Unsupported noise scalar output field')
    spatial = float(parameters.get('spatial noise coordinate scale', .001))
    temporal = float(parameters.get('time noise coordinate scale', .1))
    time_offset = float(parameters.get('time coordinate offset', 0))
    offset = parameters.get('spatial coordinate offset', (0, 0, 0))
    if isinstance(offset, str):
        offset = tuple(float(v) for v in offset.split())
    low = float(parameters.get('output minimum', 0))
    high = float(parameters.get('output maximum', 1))
    values = (*position, *offset, creation_time, spatial, temporal, time_offset, low, high)
    if len(position) != 3 or len(offset) != 3 or not all(math.isfinite(v) for v in values):
        raise ValueError('Noise scalar coordinates and range must be finite')
    time = f32(f32(f32(creation_time) + f32(time_offset)) * f32(temporal))
    point = tuple(f32(f32(f32(f32(p) + f32(o)) * f32(spatial)) + time)
                  for p, o in zip(position, offset))
    result = noise(point, tables)
    absolute = bool(parameters.get('absolute value', False))
    if absolute:
        result = abs(result)
    if parameters.get('invert absolute value', False):
        result = f32(1 - result)
    # Source angle fields store radians; alpha fields clamp to [0, 1].
    if field in (4, 12, 20):
        low, high = f32(low * math.pi / 180), f32(high * math.pi / 180)
    else:
        low, high = f32(low), f32(high)
    half = 1.0 if absolute else .5
    span = f32(high - low)
    bias = f32(f32(f32(1 - half) * span) + low)
    result = f32(f32(result * f32(span * half)) + bias)
    return min(1., max(0., result)) if field in (7, 16) else result
