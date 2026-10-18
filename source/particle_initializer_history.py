"""Ordered birth attribute writes with explicit spatial initializer callbacks.

Scene adapters provide actual sampled positions/attributes. Unknown writes
are rejected; this module does not guess parent or model spawn positions.
"""
import math


def initialize(modules, fields, position, sampler, noise_tables=None, order=None):
    from particle_sprite_state import remap_scalars
    fields = dict(fields)
    position = tuple(position)
    snapshots = []
    indices = range(len(modules)) if order is None else order
    if order is not None and (len(set(order)) != len(order) or any(
            isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(modules) for i in order)):
        raise ValueError('Invalid initializer execution indices')
    for index in indices:
        module = modules[index]
        if not module['parameters'].get('operator enabled', True):
            continue
        name = module['function']
        if name in ('Remap Noise to Scalar', 'Remap Initial Scalar'):
            fields = remap_scalars(fields, [module], position, noise_tables)
        else:
            # The sampler sees the fields before this write, so a radius-scaled
            # offset can use a preceding noise result without using a later one.
            writes, replacement = sampler(index, module, dict(fields), position)
            if any(field not in fields for field in writes):
                raise ValueError('Initializer writes an unrepresented attribute')
            fields.update(writes)
            if replacement is not None:
                position = tuple(replacement)
        if len(position) != 3 or not all(math.isfinite(v) for v in (*position, *fields.values())):
            raise ValueError('Initializer produced invalid birth attributes')
        snapshots.append({'index': index, 'fields': dict(fields), 'position': position})
    return fields, position, snapshots
