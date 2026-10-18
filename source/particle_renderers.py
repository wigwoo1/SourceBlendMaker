"""Render passes share definition identity and hence the same particle RNG.

Each pass bakes the same simulation separately, preserving its own renderer
parameters. Native shader blending and Source render ordering remain approximate.
"""
def spline_ring_enabled(definition,material,requested):
    """Normal-stream omission is valid only for the decoded spline rope path."""
    enabled=[m for m in definition['modules']['renderers'] if m['parameters'].get('operator enabled',True)]
    return bool(requested and material.get('sfm_particle_material_spline_type',0)==1
                and enabled and all(m['function']=='render_rope' for m in enabled))

def passes(definition):
    enabled=[m for m in definition['modules']['renderers'] if m['parameters'].get('operator enabled',True)]
    if len(enabled)<=1:return [definition]
    result=[]
    for index,renderer in enumerate(enabled):
        clone=dict(definition);clone['modules']={**definition['modules'],'renderers':[renderer]}
        clone['renderer_pass_index']=index;clone['renderer_pass_count']=len(enabled)
        result.append(clone)
    return result
