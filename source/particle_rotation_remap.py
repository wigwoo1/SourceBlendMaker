"""Approximate ordered scalar remaps that write particle rotation speed.

Only the installed field-8 creation-time to field-5 rotation-speed mapping is
handled here. A remap after Rotation Basic takes effect on the next simulation
tick; the one-tick correction is an explicit 120 Hz approximation.
"""
import math


def remap_speed(parameters, creation_time, current_speed):
    if int(parameters.get('input field', -1)) != 8 or int(parameters.get('output field', -1)) != 5:
        raise ValueError('Only creation-time to rotation-speed remaps are supported')
    from particle_scalar_remap import remap
    value = remap(parameters, creation_time, current_speed)
    if not math.isfinite(value):
        raise ValueError('Invalid remapped particle rotation speed')
    return value


def late_write_angle_correction(previous_speed, updated_speed, age, rotation_basic_seen, step=1/120):
    """Compensate an ordered speed write that follows Rotation Basic."""
    values = tuple(map(float, (previous_speed, updated_speed, age, step)))
    if not all(math.isfinite(value) for value in values) or age < 0 or step <= 0:
        raise ValueError('Invalid rotation-speed remap history')
    if not rotation_basic_seen:
        return 0.0
    return math.radians(updated_speed - previous_speed) * max(0.0, age - step)
