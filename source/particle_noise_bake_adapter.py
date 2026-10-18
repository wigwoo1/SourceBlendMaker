"""Development-only noise birth planning; native original effects need validation."""


def prepare(definition, planner, **options):
    from particle_noise_scalar import sample
    modules = definition['modules']['initializers']
    supported = {'Remap Noise to Scalar','Remap Initial Scalar','Lifetime Random','Radius Random',
                 'Alpha Random','Rotation Random','Rotation Yaw Random','Rotation Speed Random','Trail Length Random',
                 'Sequence Random','Sequence Two Random','Position From Control Points','Position Along Path Sequential',
                 'Position Within Box Random','Position Within Sphere Random','Position Modify Offset Random',
                 'Color Random','Remap Control Point to Vector','Rotation Yaw Flip Random','Velocity Random',
                 'Velocity Noise'}
    if any(m['function'] not in supported for m in modules if m['parameters'].get('operator enabled', True)):
        raise ValueError('Noise birth requires an unimplemented contextual initializer')
    velocity_noise = any(m['function'] == 'Velocity Noise' and m['parameters'].get('operator enabled', True) for m in modules)
    order = None
    active_modules = modules
    if velocity_noise:
        from particle_birth_passes import execution_order
        from particle_velocity_noise import settings
        order = execution_order(modules)
        active_modules = [modules[i] for i in order]
        for module in active_modules:
            if module['function'] == 'Velocity Noise':
                settings(module['parameters'])
    cleaned = {**definition, 'modules': {**definition['modules'], 'initializers':
               [m for m in active_modules if m['function'] != 'Remap Noise to Scalar']}}
    config = planner(cleaned, **options)
    for module in active_modules:
        if module['function'] != 'Remap Noise to Scalar' or not module['parameters'].get('operator enabled', True):
            continue
        p = module['parameters']
        field = int(p.get('output field', 3))
        if field not in (1, 3, 4, 5, 7, 16):
            raise ValueError('Noise field is not represented by ordered birth state')
        extremes = [sample(p, (0, 0, 0), 0, [list(range(256)) for _ in range(3)] + [[value]*256]) for value in (0., .5, 1.)]
        if field in (1, 3):
            if min(extremes) < 0:
                raise ValueError('Noise produces negative lifetime or radius')
            key = 'lifetime_range' if field == 1 else 'radius_range'
            # Conservative for culling: later authored writes can replace noise.
            config[key] = [min(*config[key], *extremes), max(*config[key], *extremes)]
    config['ordered_noise_birth'] = True
    config['initializer_order'] = order
    config['source_velocity_noise_birth'] = velocity_noise
    return config
