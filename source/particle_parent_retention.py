"""Only downstream parent-position consumers require persistent buffers."""
def required(definitions):
    result={definition.get('parent_instance_id') for definition in definitions
        if any(module['function'] in ('Position From Parent Particles','Inherit Initial Value From Parent Particle')
            and module['parameters'].get('operator enabled',True)
            for module in definition['modules'].get('initializers',[]))}
    result.update(definition.get('parent_instance_id') for definition in definitions
        if any(module['function']=='Inherit Attribute From Parent Particle' and module['parameters'].get('operator enabled',True)
               for module in definition['modules'].get('operators',[])))
    result.update(definition.get('instance_id') for definition in definitions
        if any(module['function']=='Set child control points from particle positions'
               and module['parameters'].get('operator enabled',True)
               for module in definition['modules'].get('operators',[])))
    return result

def retain(instance,required_ids,simulation_only=False,retain_leaf_contexts=True):
    return simulation_only or retain_leaf_contexts or instance in required_ids
