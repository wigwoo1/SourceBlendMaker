"""Ordered Source-space birth positions from imported control-point transforms.

The scene query returns (Source-space position, mathutils rotation). Complex
model/parent initializers require explicit handlers; none are guessed here.
"""


def bind(rng, control_query, particle_id, handlers=None, velocity_sink=None,
         highest_control_point=None):
    import math
    from mathutils import Vector
    handlers = handlers or {}

    def control(index):
        if isinstance(index, bool) or int(index) != index or not 0 <= index < 64:
            raise ValueError('Invalid birth initializer control point')
        return control_query(int(index))

    def sample(index, module, fields, position):
        name, p = module['function'], module['parameters']
        if name in handlers:
            return handlers[name](index, module, fields, position)
        if name == 'Position From Control Points':
            if float(p.get('Control Point Increment Amount', 0)) != 0:
                raise ValueError('Incrementing birth control points require collection context')
            origin, _ = control(p.get('Starting Control Point', p.get('control_point_number', 0)))
            return {}, tuple(origin)
        if name == 'Position Along Path Sequential':
            from particle_path import point, validate
            _, start, end = validate(p)
            a, _ = control(start)
            b, _ = control(end)
            return {}, point(particle_id, p, a, b)
        if name == 'Position Within Box Random':
            origin, _ = control(p.get('control_point_number', 0))
            low, high = p.get('min', (0, 0, 0)), p.get('max', (0, 0, 0))
            if len(low) != 3 or len(high) != 3:
                raise ValueError('Box birth position requires three components')
            offset = Vector(tuple(rng.uniform(float(a), float(b)) for a, b in zip(low, high)))
            return {}, tuple(Vector(origin) + offset)
        if name == 'Position Within Sphere Random':
            if p.get('create in model', 0):
                raise ValueError('Sphere birth requires an explicit model/distribution context')
            if p.get('randomly distribute to highest supplied Control Point', False):
                from particle_sphere_distribution import settings as distribution_settings, choose
                config = distribution_settings(p, highest_control_point)
                selected = choose(rng, config)
            else:
                selected = p.get('control_point_number', 0)
            origin, rotation = control(selected)
            z = rng.uniform(-1, 1)
            angle = rng.uniform(0, math.tau)
            radial = math.sqrt(max(0., 1 - z*z))
            direction = Vector((radial*math.cos(angle), radial*math.sin(angle), z))
            distance = rng.uniform(float(p.get('distance_min', 0)), float(p.get('distance_max', 0)))
            bias = p.get('distance_bias', (1, 1, 1))
            absolute = p.get('distance_bias_absolute_value', (0, 0, 0))
            if len(bias) != 3 or len(absolute) != 3:
                raise ValueError('Sphere birth bias requires three components')
            offset = Vector(tuple(direction[i]*distance*float(bias[i]) for i in range(3)))
            for i in range(3):
                if absolute[i]:
                    offset[i] = abs(offset[i])
            if p.get('bias in local system', False):
                offset = rotation @ offset
            speed = rng.uniform(float(p.get('speed_min', 0)), float(p.get('speed_max', 0)))
            low = p.get('speed_in_local_coordinate_system_min', (0, 0, 0))
            high = p.get('speed_in_local_coordinate_system_max', (0, 0, 0))
            if len(low) != 3 or len(high) != 3:
                raise ValueError('Sphere birth velocity requires three components')
            velocity = direction*speed + rotation @ Vector(tuple(rng.uniform(float(a), float(b)) for a, b in zip(low, high)))
            if velocity_sink is None and any(v != 0 for v in velocity):
                raise ValueError('Sphere birth velocity requires a motion-state sink')
            if velocity_sink is not None:
                velocity_sink(tuple(velocity))
            return {}, tuple(Vector(origin) + offset)
        if name == 'Position Modify Offset Random':
            low, high = p.get('offset min', (0, 0, 0)), p.get('offset max', (0, 0, 0))
            if len(low) != 3 or len(high) != 3:
                raise ValueError('Birth offset requires three components')
            offset = Vector(tuple(rng.uniform(float(a), float(b)) for a, b in zip(low, high)))
            if p.get('offset in local space 0/1', False):
                _, rotation = control(p.get('control_point_number', 0))
                offset = rotation @ offset
            if p.get('offset proportional to radius 0/1', False):
                offset *= fields[3]
            return {}, tuple(Vector(position) + offset)
        raise ValueError('Ordered scene initializer needs an explicit handler: ' + name)
    return sample
