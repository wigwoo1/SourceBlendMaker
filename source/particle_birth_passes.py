"""Verified two-pass initializer dispatch for experimental Velocity Noise births.

Installed collector 0x101ed050: ordinary first writers, then additive/override
initializers in authored order. Original indices are retained for collection
contexts. This is deliberately separate from the existing approximate path.
Incomplete multi-attribute callbacks are rejected before any birth is sampled.
"""

PRIMARY = {'Lifetime Random': 1 << 1, 'Radius Random': 1 << 3,
           'Rotation Random': 1 << 4, 'Rotation Speed Random': 1 << 5,
           'Color Random': 1 << 6, 'Alpha Random': 1 << 7,
           'Sequence Random': 1 << 9, 'Trail Length Random': 1 << 10,
           'Rotation Yaw Random': 1 << 12, 'Sequence Two Random': 1 << 13,
           'Position Within Box Random': 5, 'Position Within Sphere Random': 5}
OVERRIDE = {'Remap Initial Scalar', 'Position Modify Offset Random',
            'Remap Control Point to Vector', 'Rotation Yaw Flip Random',
            'Velocity Random', 'Velocity Noise'}
SHARED = {'operator start fadein': 0, 'operator end fadein': 0,
          'operator start fadeout': 0, 'operator end fadeout': 0, 'operator fade oscillate': 0,
          'operator time offset min': 0, 'operator time offset max': 0,
          'operator time scale min': 1, 'operator time scale max': 1,
          'operator strength random scale min': 1, 'operator strength random scale max': 1,
          'operator strength scale control point': -1, 'operator end cap state': -1}


def execution_order(modules):
    """Return enabled original indices, skipping later ordinary attribute writers."""
    first, second, written = [], [], 0
    for index, module in enumerate(modules):
        name, p = module['function'], module['parameters']
        if not p.get('operator enabled', True):
            continue
        if any(float(p.get(key, default)) != default for key, default in SHARED.items()):
            raise ValueError('Velocity Noise birth initializer shared timing/strength is unverified: ' + name)
        if name in ('Position From Control Points', 'Position Along Path Sequential'):
            raise ValueError('Velocity Noise birth needs complete multi-attribute initialization: ' + name)
        if name in ('Color Random', 'Alpha Random'):
            expected = 6 if name == 'Color Random' else 7
            if float(p.get('output field', expected)) != expected:
                raise ValueError('Velocity Noise birth requires the represented color/alpha field')
        if name in OVERRIDE:
            second.append(index)
            continue
        if name == 'Remap Noise to Scalar':
            field = float(p.get('output field', 3))
            if field not in (1, 3, 4, 5, 7, 16):
                raise ValueError('Velocity Noise birth scalar field is not represented')
            mask = 1 << int(field)
        elif name in PRIMARY:
            mask = PRIMARY[name]
        else:
            raise ValueError('Velocity Noise birth has an unverified initializer pass: ' + name)
        if not mask & ~written:
            continue
        if mask & written:
            raise ValueError('Velocity Noise birth needs partial multi-attribute writes: ' + name)
        first.append(index)
        written |= mask
    return first + second
