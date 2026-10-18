"""Native signed refraction pass wiring for Blender 5.2 experiments.

Not yet enabled by the production importer. Tint is connected; exact Source
tint sampling, blur, layer ordering and normal decoding need visual validation.
"""
POSITIVE='SFM_Refraction_Positive'
NEGATIVE='SFM_Refraction_Negative'
TINT='SFM_Refraction_Tint'
COVERAGE='SFM_Refraction_Coverage'

def write_tint(material,tint_socket,coverage_socket):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    weighted=nodes.new('ShaderNodeVectorMath');weighted.operation='SCALE'
    links.new(tint_socket,weighted.inputs[0]);links.new(coverage_socket,weighted.inputs['Scale'])
    color=nodes.new('ShaderNodeOutputAOV');color.aov_name=TINT
    links.new(weighted.outputs[0],color.inputs['Color'])
    coverage=nodes.new('ShaderNodeOutputAOV');coverage.aov_name=COVERAGE
    links.new(coverage_socket,coverage.inputs['Value'])

def apply_tint(tree,image_socket,render_layer_node):
    """Single-layer coverage-weighted tint; opaque compositor output."""
    nodes=tree.nodes;links=tree.links
    delta=nodes.new('ShaderNodeVectorMath');delta.operation='SUBTRACT'
    links.new(render_layer_node.outputs[TINT],delta.inputs[0])
    links.new(render_layer_node.outputs[COVERAGE],delta.inputs[1])
    factor=nodes.new('ShaderNodeVectorMath');factor.operation='ADD'
    factor.inputs[1].default_value=(1,1,1);links.new(delta.outputs[0],factor.inputs[0])
    result=nodes.new('ShaderNodeVectorMath');result.operation='MULTIPLY'
    links.new(image_socket,result.inputs[0]);links.new(factor.outputs[0],result.inputs[1])
    return result.outputs[0]

def normal_displacement(material,image,amount,vertex_modulate=False):
    """Decode packed RGB normals without lighting or normal-map Y conversion."""
    import math
    if not math.isfinite(float(amount)):raise ValueError('Invalid refraction amount')
    nodes=material.node_tree.nodes;links=material.node_tree.links
    tex=nodes.new('ShaderNodeTexImage');tex.image=image
    image.colorspace_settings.name='Non-Color'
    decode=nodes.new('ShaderNodeVectorMath');decode.operation='MULTIPLY_ADD'
    decode.inputs[1].default_value=(2,2,0);decode.inputs[2].default_value=(-1,-1,0)
    links.new(tex.outputs['Color'],decode.inputs[0])
    factor=nodes.new('ShaderNodeMath');factor.operation='MULTIPLY'
    factor.inputs[1].default_value=float(amount);links.new(tex.outputs['Alpha'],factor.inputs[0])
    alpha=factor.outputs[0]
    if vertex_modulate:
        color=nodes.new('ShaderNodeVertexColor');color.layer_name='sfm_particle_color'
        multiply=nodes.new('ShaderNodeMath');multiply.operation='MULTIPLY'
        links.new(alpha,multiply.inputs[0]);links.new(color.outputs['Alpha'],multiply.inputs[1])
        alpha=multiply.outputs[0]
    offset=nodes.new('ShaderNodeVectorMath');offset.operation='SCALE'
    links.new(decode.outputs[0],offset.inputs[0]);links.new(alpha,offset.inputs['Scale'])
    return offset.outputs['Vector']

def write_passes(material,displacement_socket):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    for name,sign in ((POSITIVE,1.),(NEGATIVE,-1.)):
        scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
        scale.inputs['Scale'].default_value=sign
        links.new(displacement_socket,scale.inputs[0])
        positive=nodes.new('ShaderNodeVectorMath');positive.operation='MAXIMUM'
        positive.inputs[1].default_value=(0,0,0)
        links.new(scale.outputs['Vector'],positive.inputs[0])
        output=nodes.new('ShaderNodeOutputAOV');output.aov_name=name
        links.new(positive.outputs['Vector'],output.inputs['Color'])

def register_passes(layer):
    for name in (POSITIVE,NEGATIVE):
        if not any(a.name==name for a in layer.aovs):layer.aovs.add().name=name
    for name,kind in ((TINT,'COLOR'),(COVERAGE,'VALUE')):
        if not any(a.name==name for a in layer.aovs):
            a=layer.aovs.add();a.name=name;a.type=kind

def signed_pass(tree,render_layer_node):
    node=tree.nodes.new('ShaderNodeVectorMath');node.operation='SUBTRACT'
    tree.links.new(render_layer_node.outputs[POSITIVE],node.inputs[0])
    tree.links.new(render_layer_node.outputs[NEGATIVE],node.inputs[1])
    return node.outputs['Vector']

def distort_background(tree,image_socket,render_layer_node,scene,uv_offset=(0.,0.)):
    """Apply normalized offsets in native pixels; follow render size changes."""
    vector=signed_pass(tree,render_layer_node)
    if uv_offset!=(0.,0.):
        bias=tree.nodes.new('ShaderNodeVectorMath');bias.operation='ADD'
        tree.links.new(vector,bias.inputs[0]);bias.inputs[1].default_value=(*uv_offset,0.)
        vector=bias.outputs[0]
    scale=tree.nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
    tree.links.new(vector,scale.inputs[0])
    for axis,key in enumerate(('resolution_x','resolution_y')):
        curve=scale.inputs[1].driver_add('default_value',axis)
        driver=curve.driver;driver.type='SCRIPTED'
        for name,path in (('size','render.'+key),('percent','render.resolution_percentage')):
            var=driver.variables.new();var.name=name;var.type='SINGLE_PROP'
            var.targets[0].id_type='SCENE';var.targets[0].id=scene
            var.targets[0].data_path=path
        driver.expression='-max(1, floor(size * percent / 100))'
    scale.inputs[1].default_value[2]=0
    node=tree.nodes.new('CompositorNodeDisplace')
    tree.links.new(image_socket,node.inputs['Image'])
    tree.links.new(scale.outputs['Vector'],node.inputs['Displacement'])
    return node.outputs['Image']

def sample_refracted_background(tree,image_socket,render_layer_node,scene,blur_amount):
    """Each blur lookup samples the original at warp + kernel offset.

    Experimental RGB path: CPU compositor is verified for small fractional
    offsets. Caller applies tint and alpha after the weighted lookups.
    """
    from particle_refraction import blur_samples
    samples=blur_samples(blur_amount)
    if blur_amount==0:return distort_background(tree,image_socket,render_layer_node,scene)
    anchor=tree.nodes.new('ShaderNodeVectorMath');anchor.operation='SCALE'
    anchor.inputs['Scale'].default_value=0;tree.links.new(image_socket,anchor.inputs[0])
    total=anchor.outputs[0]
    for x,y,weight in samples:
        sampled=distort_background(tree,image_socket,render_layer_node,scene,(x,y))
        scale=tree.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
        scale.inputs['Scale'].default_value=weight;tree.links.new(sampled,scale.inputs[0])
        add=tree.nodes.new('ShaderNodeVectorMath');add.operation='ADD'
        tree.links.new(total,add.inputs[0]);tree.links.new(scale.outputs[0],add.inputs[1]);total=add.outputs[0]
    return total

def blur_background(tree,image_socket,scene,amount):
    """Experimental Source screen-UV kernel; caller must mask particle coverage.

    RGB only. This does not implement ordered layers, silhouette fading or
    Source gamma conversion. Sampling follows current render dimensions.
    """
    from particle_refraction import blur_samples
    samples=blur_samples(amount)
    if amount==0:return image_socket
    # Keep the accumulation domain untransformed. Starting with a translated
    # sample makes later additions resample relative to that sample's domain.
    anchor=tree.nodes.new('ShaderNodeVectorMath');anchor.operation='SCALE'
    anchor.inputs['Scale'].default_value=0;tree.links.new(image_socket,anchor.inputs[0])
    total=anchor.outputs[0]
    for x,y,weight in samples:
        sample=tree.nodes.new('CompositorNodeTranslate')
        sample.inputs['Interpolation'].default_value='Bilinear'
        for axis,key,offset in (('X','resolution_x',x),('Y','resolution_y',y)):
            curve=sample.inputs[axis].driver_add('default_value')
            driver=curve.driver;driver.type='SCRIPTED'
            for name,path in (('size','render.'+key),('percent','render.resolution_percentage')):
                var=driver.variables.new();var.name=name;var.type='SINGLE_PROP'
                var.targets[0].id_type='SCENE';var.targets[0].id=scene;var.targets[0].data_path=path
            driver.expression=f'{-offset!r} * max(1, floor(size * percent / 100))'
        tree.links.new(image_socket,sample.inputs['Image'])
        scale=tree.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
        scale.inputs['Scale'].default_value=weight;tree.links.new(sample.outputs[0],scale.inputs[0])
        if total is None:total=scale.outputs[0]
        else:
            add=tree.nodes.new('ShaderNodeVectorMath');add.operation='ADD'
            tree.links.new(total,add.inputs[0]);tree.links.new(scale.outputs[0],add.inputs[1]);total=add.outputs[0]
    return total

def blend_coverage(tree,original_socket,effect_socket,coverage_socket):
    """Single-layer RGB interpolation, with coverage clamped to [0, 1].

    Original input anchors the image domain. Overlapping particle layers still
    require independent ordered composition; summed coverage is not that model.
    """
    low=tree.nodes.new('ShaderNodeMath');low.operation='MAXIMUM'
    low.inputs[1].default_value=0;tree.links.new(coverage_socket,low.inputs[0])
    high=tree.nodes.new('ShaderNodeMath');high.operation='MINIMUM'
    high.inputs[1].default_value=1;tree.links.new(low.outputs[0],high.inputs[0])
    difference=tree.nodes.new('ShaderNodeVectorMath');difference.operation='SUBTRACT'
    tree.links.new(effect_socket,difference.inputs[0]);tree.links.new(original_socket,difference.inputs[1])
    scale=tree.nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
    tree.links.new(difference.outputs[0],scale.inputs[0]);tree.links.new(high.outputs[0],scale.inputs['Scale'])
    add=tree.nodes.new('ShaderNodeVectorMath');add.operation='ADD'
    tree.links.new(original_socket,add.inputs[0]);tree.links.new(scale.outputs[0],add.inputs[1])
    return add.outputs[0]

def composite_refraction_layer(tree,original_socket,warped_socket,render_layer_node):
    """Single Source-style alpha layer, using premultiplied tint and coverage.

    Original*(1-coverage) + warped*(tint*coverage). AOV tint already contains
    coverage. This excludes silhouette fading and ordered overlapping layers.
    """
    remaining=tree.nodes.new('ShaderNodeMath');remaining.operation='SUBTRACT'
    remaining.inputs[0].default_value=1
    tree.links.new(render_layer_node.outputs[COVERAGE],remaining.inputs[1])
    original=tree.nodes.new('ShaderNodeVectorMath');original.operation='SCALE'
    tree.links.new(original_socket,original.inputs[0]);tree.links.new(remaining.outputs[0],original.inputs['Scale'])
    effect=tree.nodes.new('ShaderNodeVectorMath');effect.operation='MULTIPLY'
    tree.links.new(warped_socket,effect.inputs[0]);tree.links.new(render_layer_node.outputs[TINT],effect.inputs[1])
    result=tree.nodes.new('ShaderNodeVectorMath');result.operation='ADD'
    tree.links.new(original.outputs[0],result.inputs[0]);tree.links.new(effect.outputs[0],result.inputs[1])
    return result.outputs[0]
