"""Experimental independent refraction AOV namespaces; no production routing.

One material namespace must belong to one independent primitive/layer. Sharing
it across overlapping particles still sums them. Source draw order is unverified.
"""
from types import SimpleNamespace
from particle_refraction_nodes import POSITIVE,NEGATIVE,TINT,COVERAGE

def isolate_material(material,layer_name):
    if not layer_name or not layer_name.isidentifier():raise ValueError('Invalid layer identifier')
    copy=material.copy();copy.name=material.name+' '+layer_name
    expected={POSITIVE,NEGATIVE,TINT,COVERAGE}
    found=set()
    for node in copy.node_tree.nodes:
        if node.bl_idname=='ShaderNodeOutputAOV' and node.aov_name in expected:
            found.add(node.aov_name);node.aov_name+='_'+layer_name
    if found!=expected:raise ValueError('Material lacks complete refraction passes')
    return copy

def register_layer(view_layer,layer_name):
    if not layer_name or not layer_name.isidentifier():raise ValueError('Invalid layer identifier')
    for name in (POSITIVE,NEGATIVE,TINT,COVERAGE):
        full=name+'_'+layer_name
        if not any(a.name==full for a in view_layer.aovs):
            a=view_layer.aovs.add();a.name=full;a.type='VALUE' if name==COVERAGE else 'COLOR'

def layer_outputs(render_node,layer_name):
    return SimpleNamespace(outputs={name:render_node.outputs[name+'_'+layer_name]
                                   for name in (POSITIVE,NEGATIVE,TINT,COVERAGE)})

def assign_baked_layers(scene,objects,camera):
    """Experimental per-frame meshes, sharing namespaces by sorted rank.

    Requires mutually exclusive baked frame meshes. Depth order is baked for
    the supplied animated camera; editing that camera requires reassignment.
    Returns namespaces in composition order. No particle-count truncation.
    """
    from mathutils import Vector
    from particle_refraction_order import back_to_front
    objects=list(objects);seen=set();prepared=[]
    for obj in objects:
        frame=obj.get('sfm_baked_frame')
        if frame is None or frame in seen:raise ValueError('Expected one exclusive mesh per baked frame')
        seen.add(frame)
        if len(obj.data.materials)!=1:raise ValueError('Expected one original material per frame mesh')
        prepared.append((obj,frame,obj.data.materials[0]))
    original_frame=scene.frame_current;cache={};count=0
    try:
        for obj,frame,base in prepared:
            scene.frame_set(int(frame))
            centers=[obj.matrix_world@p.center for p in obj.data.polygons]
            forward=camera.matrix_world.to_quaternion()@Vector((0,0,-1))
            order=back_to_front(centers,camera.matrix_world.translation,forward)
            for rank,index in enumerate(order):
                name='rank_'+str(rank);key=(base.as_pointer(),rank)
                if key not in cache:cache[key]=isolate_material(base,name)
                obj.data.materials.append(cache[key]);obj.data.polygons[index].material_index=len(obj.data.materials)-1
            count=max(count,len(order))
    finally:scene.frame_set(original_frame)
    names=['rank_'+str(rank) for rank in range(count)]
    for name in names:register_layer(scene.view_layers[0],name)
    return names
