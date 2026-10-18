"""Preserve particle child instance identity on native Blender objects."""
def tag(obj,definition):
    obj['sfm_particle_instance_id']=int(definition.get('instance_id',-1))
    parent=definition.get('parent_instance_id')
    obj['sfm_particle_parent_instance_id']=-1 if parent is None else int(parent)
    obj['sfm_particle_random_instance_index']=int(definition.get('random_instance_index',0))
    obj['sfm_particle_renderer_pass']=int(definition.get('renderer_pass_index',0))
