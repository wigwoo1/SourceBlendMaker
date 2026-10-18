"""Experimental bridge from baked sprite state to Source-unit pull integration.

Caller supplies CP positions on collection simulation time, already mapped to
the shot clock when needed. No production gate is changed by this module.
"""
from particle_pull_settings import settings
from particle_pull_integrator import simulate, vec
from particle_random_force_history import history
import math

def position(definition, state, age, scale, birth_position, target_at_clock):
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Particle scale must be positive')
    age=float(age)
    if not math.isfinite(age) or age<0 or math.ceil(age*120)>100000:
        raise ValueError('Particle age exceeds experimental integration bounds')
    forces=[m for m in definition['modules'].get('forces',[])
            if m['parameters'].get('operator enabled',True)]
    unknown=[m['function'] for m in forces if m['function'].casefold() not in
             ('pull towards control point','random force','twist around axis')]
    if unknown:
        raise ValueError('Unsupported combined forces: '+', '.join(unknown))
    pulls=[m for m in definition['modules'].get('forces',[])
           if m['function'].casefold()=='pull towards control point'
           and m['parameters'].get('operator enabled',True)]
    if len(pulls)!=1:
        raise ValueError('Experimental adapter requires exactly one pull force')
    parsed=settings(pulls[0]['parameters'])
    if parsed['prototype_unsupported_features']:
        raise ValueError('; '.join(parsed['prototype_unsupported_features']))
    origin=vec(birth_position)
    clock=float(state['creation_simulation_time'])
    def target(relative_age):
        point=vec(target_at_clock(parsed['control_point'],clock+relative_age))
        return tuple((point[i]-origin[i])/scale for i in range(3))
    movements=[m['parameters'] for m in definition['modules']['operators']
               if m['function']=='Movement Basic' and m['parameters'].get('operator enabled',True)]
    if len(movements)!=1:
        raise ValueError('Requires exactly one Movement Basic operator')
    motion=movements[0]
    for label,parameters in [('Movement Basic',motion)]+[
            ('random force',m['parameters']) for m in forces if m['function'].casefold()=='random force']:
        common={key:value for key,value in parameters.items() if key.startswith('operator ')}
        unsupported=settings(common)['prototype_unsupported_features']
        if unsupported:
            raise ValueError(label+': '+'; '.join(unsupported))
    signature=(state['force_seed'],tuple((m['function'],bool(m['parameters'].get('operator enabled',True)),
               tuple(m['parameters'].get('min force',(0,0,0))),tuple(m['parameters'].get('max force',(0,0,0))))
               for m in definition['modules']['forces']))
    cached=state.get('_pull_random_history')
    if cached is None or cached[0]!=signature:
        cached=(signature,history(definition['modules']['forces'],state['force_seed']))
        state['_pull_random_history']=cached
    random=cached[1]
    from particle_twist_axis import settings as twist_settings,acceleration as twist_acceleration
    twists=[twist_settings(m['parameters']) for m in forces if m['function'].casefold()=='twist around axis']
    def spatial_force(point,relative_age):
        result=[0.,0.,0.]
        for twist in twists:
            destination=vec(target_at_clock(twist['control_point'],clock+relative_age))
            relative_origin=tuple((destination[i]-origin[i])/scale for i in range(3))
            force=twist_acceleration(twist,point,relative_origin)
            result=[a+b for a,b in zip(result,force)]
        return result
    boundaries=[tick/60 for tick in range(1,math.ceil(age*60))]
    result,_=simulate(tuple(v/scale for v in state['offset']),tuple(v/scale for v in state['velocity']),
                      age,target,parsed['amount'],parsed['power'],birth_clock=clock,
                      component_scale=parsed['component_scale'],gravity=motion.get('gravity',(0,0,0)),
                      drag=motion.get('drag',0),external_force=random,force_boundaries=boundaries,
                      spatial_force=spatial_force if twists else None)
    return tuple(origin[i]+result[i]*scale for i in range(3))
