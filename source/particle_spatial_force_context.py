"""Bind ordered world-space forces to a particle's birth-relative coordinates.

The caller supplies Blender world control points at collection-clock times.
This adapter does not evaluate transforms or change the current scene frame.
Local twist axes and Source runtime timing parity remain unsupported.
"""
import math
from particle_vector_history import vector

def ordered_movement_supported(definition, allow_translation_lock=False):
    """The decoded drag range and CP locks bound this ordered force path."""
    operators=[m for m in definition['modules']['operators'] if m['parameters'].get('operator enabled',True)]
    if not allow_translation_lock and any(m['function']=='Movement Lock to Control Point' for m in operators):return False
    movements=[m for m in operators if m['function']=='Movement Basic']
    if len(movements)!=1:return False
    drag=float(movements[0]['parameters'].get('drag',0))
    return math.isfinite(drag) and 0<=drag<=.9999

def bind(modules, birth_position, scale, birth_clock, target_at_clock):
    scale=float(scale); birth_clock=float(birth_clock)
    if not math.isfinite(scale) or scale<=0 or not math.isfinite(birth_clock):
        raise ValueError('Invalid spatial force scale or birth clock')
    birth=vector(birth_position)
    prepared=[]
    for module in modules:
        p=module['parameters']
        if not p.get('operator enabled',True):continue
        name=module['function']
        if name=='random force':continue  # Independent time-only callback.
        if name.casefold()=='pull towards control point':
            from particle_pull_settings import settings
            from particle_pull_acceleration import acceleration as pull_acceleration
            config=settings(p)
            if config['prototype_unsupported_features']:
                raise ValueError('; '.join(config['prototype_unsupported_features']))
            prepared.append((config['control_point'],config,
                             lambda cfg,pos,origin:pull_acceleration(pos,origin,cfg['amount'],cfg['power'],cfg['component_scale'])))
        elif name.casefold()=='twist around axis':
            from particle_twist_axis import settings, acceleration
            config=settings(p)
            prepared.append((config['control_point'],config,acceleration))
        elif name=='Force based on distance from plane':
            from particle_plane_force import settings, acceleration_prepared
            config=settings(p)
            prepared.append((config['Control point number'],config,
                             lambda cfg,pos,origin:acceleration_prepared(pos,origin,cfg)))
        else:raise ValueError('Unsupported ordered spatial force: '+name)

    def acceleration_at(age, relative_position):
        if not math.isfinite(age) or age<0:raise ValueError('Invalid spatial force age')
        relative=vector(relative_position)
        position=tuple((b+x)/scale for b,x in zip(birth,relative))
        total=[0.,0.,0.]
        for cp,config,compute in prepared:
            origin=tuple(v/scale for v in vector(target_at_clock(cp,birth_clock+age)))
            value=vector(compute(config,position,origin))
            for i in range(3):total[i]+=value[i]*scale
        return vector(total)
    return acceleration_at
