"""Scene integration for the opt-in experimental particle refraction path.

Current scope: baked per-frame effects and a single local render-layer image.
Meshes must be mutually exclusive within each effect. Source parity is unverified.
"""
def install(scene,objects):
    import bpy,json
    from particle_refraction import blur_samples
    from particle_refraction_layers import layer_outputs
    from particle_refraction_multi import assign
    from particle_refraction_nodes import sample_refracted_background,composite_refraction_layer
    objects=list(objects)
    if scene.camera is None:raise ValueError('Refraction requires an active camera')
    if not objects:raise ValueError('No refraction frame meshes supplied')
    existing=scene.compositing_node_group
    if existing is not None:
        candidates=[n for n in existing.nodes if n.bl_idname=='CompositorNodeRLayers' and n.scene in (None,scene) and n.layer==scene.view_layers[0].name]
        if len(candidates)!=1:raise ValueError('Existing compositor requires one local primary render-layer node')
        if not candidates[0].outputs['Image'].is_linked:raise ValueError('Existing compositor has no connected render image')
    overlay_objects=[obj for obj in objects if json.loads(obj.data.materials[0]['sfm_refraction_settings']).get('authored_shader_features',{}).get('ignore_depth')]
    layers=assign(scene,objects,scene.camera)
    if existing is not None:
        group=existing.copy();group.name=scene.name+' with experimental particle refraction'
        rendered=group.nodes[candidates[0].name]
        destinations=[link.to_socket for link in rendered.outputs['Image'].links]
    else:
        group=bpy.data.node_groups.new(scene.name+' experimental particle refraction','CompositorNodeTree')
        group.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
        rendered=group.nodes.new('CompositorNodeRLayers');rendered.scene=scene
        output=group.nodes.new('NodeGroupOutput');destinations=[output.inputs['Image']]
    # Refresh sockets after registering namespaced AOVs.
    scene.compositing_node_group=group
    rendered.scene=scene
    overlay_rendered=None
    if overlay_objects:
        from particle_refraction_overlay import pass_scene
        from particle_refraction_layers import register_layer
        auxiliary=pass_scene(scene,overlay_objects)
        for name,blur,overlay in layers:
            if overlay:register_layer(auxiliary.view_layers[0],name)
        overlay_rendered=group.nodes.new('CompositorNodeRLayers');overlay_rendered.scene=auxiliary
    current=rendered.outputs['Image']
    for name,blur,overlay in layers:
        passes=layer_outputs(overlay_rendered if overlay else rendered,name)
        sampled=sample_refracted_background(group,current,passes,scene,blur)
        current=composite_refraction_layer(group,current,sampled,passes)
    for destination in destinations:group.links.new(current,destination)
    scene.compositing_node_group=group
    scene.render.compositor_device='CPU'
    scene['sfm_experimental_refraction']=json.dumps({'layers':len(layers),'blur_values':sorted(set(blur for name,blur,overlay in layers)),'ignore_depth_pass_scene':auxiliary.name if overlay_objects else None,'existing_compositor_preserved':existing is not None,'compositor_device':'CPU','source_visual_parity':False,'limitations':['Camera depth approximation; rebake ordering after camera edits','Caller must supply mutually exclusive meshes per effect and matching sample frames','Reflection and shot phase unfinished; silhouette fade needs Source visual comparison','Output RGB composition does not preserve transparent-film alpha']})
    return group
