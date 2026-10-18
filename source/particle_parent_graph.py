"""Simulation-instance scheduling before renderer-pass expansion.

Effect names can repeat. Instance IDs, not names or renderer passes, identify
parent buffers. This planner does not simulate effects or enable new operators.
"""


def ordered(definitions):
    by_id={}
    for definition in definitions:
        identity=definition.get('instance_id')
        if not isinstance(identity,int) or isinstance(identity,bool):
            raise ValueError('Particle simulation requires integer instance IDs')
        if identity in by_id:raise ValueError('Duplicate particle simulation instance ID')
        by_id[identity]=definition
    result=[];done=set()
    for identity in by_id:
        chain=[];active=set()
        while identity is not None and identity not in done:
            if identity in active:raise ValueError('Cyclic particle simulation dependency')
            if identity not in by_id:raise ValueError('Missing particle parent instance')
            active.add(identity);chain.append(identity)
            identity=by_id[identity].get('parent_instance_id')
        for identity in reversed(chain):
            done.add(identity);result.append(by_id[identity])
    return result
