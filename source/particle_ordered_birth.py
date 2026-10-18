"""Assemble an ordered particle birth for the Blender bake adapter.

Positions/control queries use Source units. Complex contextual initializers
must be provided explicitly. Source RNG and engine tick parity are unverified.
"""
import math


def sample(definition, rng, scale, creation_time, particle_id, control_query,
           initial_position, sequence_context=None, tint_query=None,
           handlers=None, noise_tables=None, highest_control_point=None, initializer_order=None):
    from mathutils import Vector
    from particle_initializer_history import initialize
    from particle_initializer_sampler import bind as scalar
    from particle_initializer_spatial import bind as spatial
    from particle_sprite_state import linear_color, sample_yaw_flip
    from particle_distribution import color_bytes
    base = definition['parameters']
    color = base.get('color', [255]*4)
    rgb = linear_color(color)
    velocity = Vector((0, 0, 0))
    yaw_flip = False
    outline_rgb=(1.,1.,1.)
    extra_handlers = handlers or {}

    def add_velocity(value):
        nonlocal velocity
        velocity += Vector(value)

    def auxiliary(index, module, fields, position):
        nonlocal rgb, yaw_flip, outline_rgb
        name, p = module['function'], module['parameters']
        if name in extra_handlers:
            return extra_handlers[name](index, module, fields, position)
        if name == 'Color Random':
            if p.get('output field',6)==22:
                outline_rgb=tuple(v/255 for v in color_bytes({name:p},color,rng))
                return {},None
            if float(p.get('tint_perc', 0)) != 0:
                if tint_query is None:
                    raise ValueError('Ordered tinted birth requires a lighting query')
                from particle_tint_color import color as tinted
                rgb = tinted(p, color, rng, tint_query)
            else:
                rgb = linear_color(color_bytes({name: p}, color, rng))
            return {}, None
        if name == 'Remap Control Point to Vector':
            from particle_cp_vector_color import color as remap_color, settings
            cp, _ = control_query(settings(p)['control_point'])
            rgb = list(remap_color(p, cp, rgb, creation_time))
            return {}, None
        if name == 'Rotation Yaw Flip Random':
            yaw_flip = sample_yaw_flip(p, rng)
            from particle_yaw import flip
            return ({12: flip(fields[12])} if yaw_flip else {}), None
        if name == 'Velocity Random':
            from particle_velocity import sample as sample_velocity, validate
            _, rotation = control_query(validate(p))
            world, local = sample_velocity(p, rng)
            add_velocity(Vector(world) + rotation @ Vector(local))
            return {}, None
        if name == 'Velocity Noise':
            from particle_velocity_noise import sample as noise_velocity, settings
            config = settings(p)
            rotation = None
            if config['Apply Velocity in Local Space (0/1)']:
                _, orientation = control_query(config['Control Point Number'])
                rotation = tuple(tuple(row) for row in orientation.to_matrix())
            add_velocity(noise_velocity(p, position, fields[8], noise_tables, rotation))
            return {}, None
        raise ValueError('Ordered birth requires a contextual handler: ' + name)

    names = ('Color Random', 'Remap Control Point to Vector', 'Rotation Yaw Flip Random', 'Velocity Random', 'Velocity Noise')
    spatial_handlers = {name: auxiliary for name in names}
    spatial_handlers.update({name: auxiliary for name in extra_handlers})
    sampler = scalar(rng, spatial(rng, control_query, particle_id, spatial_handlers,
                                   add_velocity, highest_control_point), base,
                    sequence_context)
    fields = {1: float(base.get('lifetime', 1)), 3: float(base.get('radius', 1)),
              4: 0., 5: float(base.get('rotation_speed', 0)), 7: color[3]/255.,
              8: creation_time, 9: int(base.get('sequence_number', 0)), 10: .1,
              11: particle_id, 12: 0., 13:float(base.get('sequence_number 1',0)), 16: 1.}
    modules = definition['modules']['initializers']
    if initializer_order is None and any(m['function'] == 'Velocity Noise' and m['parameters'].get('operator enabled', True) for m in modules):
        from particle_birth_passes import execution_order
        initializer_order = execution_order(modules)
    fields, position, history = initialize(modules, fields, initial_position, sampler, noise_tables, order=initializer_order)
    if fields[1] < 0 or fields[3] < 0 or fields[10] < 0:
        raise ValueError('Ordered birth has invalid lifetime/radius/trail duration')
    if not all(math.isfinite(v) for v in (*velocity, *rgb)):
        raise ValueError('Ordered birth has nonfinite motion/color')
    from particle_scalar_oscillation import sample as scalar_sample
    from particle_vector_history import sample as vector_sample
    operators = definition['modules']['operators']
    state = {'position': Vector(position)*scale, 'offset': Vector((0, 0, 0)),
             'velocity': velocity*scale, 'rgb': list(rgb), 'outline_rgb':outline_rgb,'outline_alpha':1., 'alpha': min(1., max(0., fields[7])),
             'secondary_alpha': fields[16], 'angle': math.radians(fields[4]),
             'rotation_speed': fields[5], 'yaw': fields[12], 'yaw_flip': yaw_flip, 'sequence': int(fields[9]),'secondary_sequence':int(fields[13]),
             'trail_duration': fields[10], 'radius': fields[3], 'lifetime': fields[1],
             'creation_simulation_time': creation_time,
             'force_seed': rng.getrandbits(64) if any(m['parameters'].get('operator enabled', True) for m in definition['modules'].get('forces', [])) else 0,
             'scalar_oscillations': {i: scalar_sample(m['parameters'], rng) for i, m in enumerate(operators) if m['function']=='Oscillate Scalar' and m['parameters'].get('operator enabled', True)},
             'vector_oscillations': {i: vector_sample(m['parameters'], rng) for i, m in enumerate(operators) if m['function']=='Oscillate Vector' and m['parameters'].get('operator enabled', True)}}
    from particle_scalar_ramp import sample_operators
    state['scalar_oscillations'].update(sample_operators(operators,rng))
    return state, history
