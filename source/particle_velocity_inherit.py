"""Installed SFM velocity-inheritance arithmetic, not yet bound to baking.

Evidence: pet.dll initializer 0x1022ef00, SHA256 recorded in diagnostics/
current_F_velocity_inherit_static_20261014.json. Inputs use Source units.
The caller must supply the engine-equivalent current/previous CP buffers and
collection timing fields. This module does not infer those from render frames.
"""
import math
from particle_scalar_oscillation import f32


def previous_position_delta(current_cp, previous_cp, interval_48,
                            interval_4c, clock_54, owner_3bc, owner_3c8,
                            velocity_scale):
    """Return XYZ added to previous particle position by the initializer.

    Offset-based timing names are intentional until their collection semantics
    are independently established. Missing/invalid inputs must not become a
    fabricated stationary control point. A gated-out initializer writes zero.
    """
    if len(current_cp) != 3 or len(previous_cp) != 3:
        raise ValueError('Control-point history requires two XYZ positions')
    values = (*current_cp, *previous_cp, interval_48, interval_4c,
              clock_54, owner_3bc, owner_3c8, velocity_scale)
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('Finite control-point history and timing required')
    current_cp, previous_cp = [tuple(map(f32, p)) for p in (current_cp, previous_cp)]
    dt, previous_dt, clock, lower, upper, scale = map(
        f32, (interval_48, interval_4c, clock_54, owner_3bc, owner_3c8, velocity_scale))
    if dt <= 0:
        return (0., 0., 0.)
    reciprocal = f32(1. / dt)
    motion = tuple(f32(reciprocal * f32(f32(c - p) * previous_dt))
                   for c, p in zip(current_cp, previous_cp))
    # SSE sums y*y + z*z, then x*x, and takes a scalar square root.
    length_squared = f32(f32(f32(motion[1]*motion[1]) + f32(motion[2]*motion[2]))
                         + f32(motion[0]*motion[0]))
    length = f32(math.sqrt(length_squared))
    if length >= 100. or max(lower, f32(upper + clock)) <= dt:
        return (0., 0., 0.)
    return tuple(-f32(scale * component) for component in motion)
