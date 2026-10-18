"""Distinguish empty child containers from unimplemented parent simulation."""
def no_birth_source(definition):
    """Return true when a root definition cannot create or receive particles.

    This is deliberately conservative: child-linked definitions and definitions
    initialized from parent particles must still flow through the simulator.
    """
    parameters=definition.get('parameters',{})
    if definition.get('parent_instance_id') is not None:return False
    if definition.get('children'):return False
    if int(parameters.get('initial_particles',0) or 0)!=0:return False
    modules=definition.get('modules',{})
    if any(m.get('parameters',{}).get('operator enabled',True)
           for m in modules.get('emitters',[])):return False
    if any(m.get('function')=='Position From Parent Particles'
           and m.get('parameters',{}).get('operator enabled',True)
           for m in modules.get('initializers',[])):return False
    return True


def empty_container(definition,required_parent_ids=()):
    return (definition.get('instance_id') not in required_parent_ids
            and not definition.get('parameters',{}).get('initial_particles',0)
            and controller_reason(definition) is None)

def controller_reason(definition):
    modules=[]
    for group in ('emitters','initializers','operators','forces','constraints'):
        for module in definition['modules'].get(group,[]):
            if module['parameters'].get('operator enabled',True):
                modules.append(group+': '+module['function'])
    return 'Non-rendering particle controller requires simulation: '+'; '.join(modules) if modules else None
