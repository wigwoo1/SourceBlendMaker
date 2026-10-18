"""Sample scalar birth writes in authored order; scene supplies spatial writes.

Random streams remain converter streams. Position/model/parent operations
must be supplied by the scene adapter and are never silently skipped.
"""
import math
from particle_distribution import random_float_exp, rotation_angle


def bind(rng, spatial_sampler, definition, sequence_context=None):
    def sample(index, module, fields, position):
        name, p = module['function'], module['parameters']
        if name in ('Radius Random', 'Lifetime Random'):
            prefix, field = ('radius', 3) if name == 'Radius Random' else ('lifetime', 1)
            default = 1 if field == 3 else 0
            value = random_float_exp(rng, p.get(prefix + '_min', default), p.get(prefix + '_max', default),
                                     p.get(prefix + '_random_exponent', 1))
            return {field: value}, None
        if name == 'Alpha Random':
            value = random_float_exp(rng, p.get('alpha_min', 255), p.get('alpha_max', 255),
                                     p.get('alpha_random_exponent', 1)) / 255
            return {7: value}, None
        if name == 'Rotation Random':
            return {4: math.degrees(rotation_angle({name: p}, rng))}, None
        if name == 'Rotation Yaw Random':
            from particle_yaw import random_angle
            return {12: random_angle(p, rng)}, None
        if name == 'Rotation Speed Random':
            value = float(p.get('rotation_speed_constant', definition.get('rotation_speed', 0)))
            value += rng.uniform(float(p.get('rotation_speed_random_min', 0)), float(p.get('rotation_speed_random_max', 0)))
            if p.get('randomly_flip_direction', False) and rng.random() < .5:
                value = -value
            return {5: value}, None
        if name == 'Trail Length Random':
            return {10: rng.uniform(float(p.get('length_min', .1)), float(p.get('length_max', .1)))}, None
        if name == 'Sequence Random':
            context=(sequence_context.get(index) if isinstance(sequence_context,dict) else sequence_context)
            if context is None:
                raise ValueError('Ordered sequence initializer requires collection context')
            return {9: context.next()}, None
        if name == 'Sequence Two Random':
            from particle_secondary_sequence import sample as sample_secondary
            return {13: sample_secondary(p,rng)}, None
        return spatial_sampler(index, module, fields, position)
    return sample
