"""Experimental packed image animation, with explicit scene-time drivers."""
def texture_frames(material,images,scene,rate,start_frame=1,time_offset=0):
    import math
    images=list(images)
    if not images:raise ValueError('No texture frames')
    if not math.isfinite(rate) or rate<=0:raise ValueError('Invalid texture frame rate')
    if not math.isfinite(start_frame) or not math.isfinite(time_offset):raise ValueError('Invalid texture animation phase')
    nodes=material.node_tree.nodes;links=material.node_tree.links
    color=alpha=None
    for index,image in enumerate(images):
        texture=nodes.new('ShaderNodeTexImage');texture.image=image
        selector=nodes.new('ShaderNodeValue')
        driver=selector.outputs[0].driver_add('default_value').driver;driver.type='SCRIPTED'
        for name,path in (('fps','render.fps'),('base','render.fps_base')):
            variable=driver.variables.new();variable.name=name;variable.type='SINGLE_PROP'
            variable.targets[0].id_type='SCENE';variable.targets[0].id=scene;variable.targets[0].data_path=path
        driver.expression=f'floor(max(0,(frame-{start_frame!r})*base/fps+{time_offset!r})*{rate!r})%{len(images)}=={index}'
        contribution=nodes.new('ShaderNodeVectorMath');contribution.operation='SCALE'
        links.new(texture.outputs['Color'],contribution.inputs[0]);links.new(selector.outputs[0],contribution.inputs['Scale'])
        opacity=nodes.new('ShaderNodeMath');opacity.operation='MULTIPLY'
        links.new(texture.outputs['Alpha'],opacity.inputs[0]);links.new(selector.outputs[0],opacity.inputs[1])
        if color is None:color=contribution.outputs[0];alpha=opacity.outputs[0]
        else:
            add=nodes.new('ShaderNodeVectorMath');add.operation='ADD'
            links.new(color,add.inputs[0]);links.new(contribution.outputs[0],add.inputs[1]);color=add.outputs[0]
            add_alpha=nodes.new('ShaderNodeMath');add_alpha.operation='ADD'
            links.new(alpha,add_alpha.inputs[0]);links.new(opacity.outputs[0],add_alpha.inputs[1]);alpha=add_alpha.outputs[0]
    return color,alpha
