"""Scalar parent inheritance at child birth, from installed PET 0x10221bc0.

Lifetime/radius only. Parent active-list order and simulation timing remain
the converter's approximations; Source RNG and killed-parent parity unverified.
"""
import math
from particle_scalar_oscillation import f32

NAME = 'Inherit Initial Value From Parent Particle'


class Initializer:
    def __init__(self, parameters):
        defaults = {'operator start fadein': 0, 'operator end fadein': 0,
                    'operator start fadeout': 0, 'operator end fadeout': 0,
                    'operator fade oscillate': 0, 'operator time offset min': 0,
                    'operator time offset max': 0, 'operator time scale min': 1,
                    'operator time scale max': 1, 'operator strength random scale min': 1,
                    'operator strength random scale max': 1,
                    'operator strength scale control point': -1, 'operator end cap state': -1}
        if any(float(parameters.get(key, value)) != value for key, value in defaults.items()):
            raise ValueError('Parent attribute strength/time gates remain unverified')
        if not parameters.get('run for killed parent particles', True):
            raise ValueError('Parent attribute killed-parent filtering remains unverified')
        self.field = parameters.get('Inherited Field', 3)
        if isinstance(self.field, bool) or not isinstance(self.field, int) or self.field not in (1, 3):
            raise ValueError('Parent attributes currently support lifetime and radius only')
        increment = parameters.get('Particle Increment Amount', 1)
        if isinstance(increment, bool) or not isinstance(increment, int) or not 0 <= increment <= 0x7fffffff:
            raise ValueError('Nonnegative integer parent attribute increment required')
        scale = float(parameters.get('Scale', 1))
        if not math.isfinite(scale) or scale < 0:
            raise ValueError('Nonnegative finite parent lifetime/radius scale required')
        self.scale = f32(scale)
        if not math.isfinite(self.scale):
            raise ValueError('Finite float32 parent attribute scale required')
        self.increment = increment
        self.random = bool(parameters.get('Random Parent Particle Distribution', False))
        self.cursor = 0

    def initialize(self, values, random_draw=None):
        if values is None or not values:
            return None
        if self.random:
            if random_draw is None or not math.isfinite(random_draw) or not 0 <= random_draw < 1:
                raise ValueError('Parent attribute random draw must be in [0,1)')
            index = math.trunc(f32(f32(len(values)) * f32(random_draw)))
        else:
            index = 0 if self.cursor > len(values) - 1 else self.cursor
        if not 0 <= index < len(values):
            raise ValueError('Parent attribute index outside active buffer')
        following = index + self.increment
        if following > 0x7fffffff:
            raise ValueError('Parent attribute cursor overflow remains unverified')
        value = float(values[index])
        if not math.isfinite(value):
            raise ValueError('Finite parent scalar required')
        result = f32(f32(value) * self.scale)
        if not math.isfinite(result):
            raise ValueError('Finite inherited parent scalar required')
        self.cursor = following
        return result


def prepare(definition):
    """Support a terminal scalar-copy suffix, preserving authored write order."""
    modules = [module for module in definition['modules'].get('initializers', [])
               if module['parameters'].get('operator enabled', True)]
    indices = [index for index, module in enumerate(modules) if module['function'] == NAME]
    if not indices:
        return []
    if any(module['function'] != NAME for module in modules[indices[0]:]):
        raise ValueError('Parent attribute inheritance must follow other initializers')
    if sum(module['function'] == 'Position From Parent Particles' for module in modules) != 1:
        raise ValueError('Parent attributes require a supported parent-position initializer')
    if any(module['function'] == 'lifetime from sequence' for module in modules):
        raise ValueError('Parent attribute and sequence lifetime ordering remains unverified')
    if any(module['function'] == 'emit to maintain count' and module['parameters'].get('operator enabled', True)
           for module in definition['modules'].get('emitters', [])):
        raise ValueError('Maintained emission with inherited lifetime requires lifecycle integration')
    return [Initializer(modules[index]['parameters']) for index in indices]
