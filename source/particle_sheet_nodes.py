"""Native geometry-node atlas UVs for maintained sprite slots."""

def material_with_sheet_uv(material):
    copy=material.copy();copy.name=material.name+' maintained atlas'
    nodes=copy.node_tree.nodes;links=copy.node_tree.links
    uv=nodes.new('ShaderNodeAttribute');uv.attribute_name='sfm_particle_uv'
    images=[node for node in nodes if node.type=='TEX_IMAGE']
    if len(images)!=1:raise ValueError('Maintained atlas requires one base image')
    links.new(uv.outputs['Vector'],images[0].inputs['Vector'])
    return copy

def store_uv(graph,geometry,age,fraction,sheet,sequences,renderer,attribute,math_node):
    from particle_sheet import animation_rate
    nodes=graph.nodes;links=graph.links
    rectangle=[0.,0.,0.,0.]
    branches=sum(len(sheet[str(sequence)]['frames']) for sequence in sequences)
    if branches>1024:raise ValueError('Maintained atlas exceeds 1024 frame branches')
    for sequence in sequences:
        entry=sheet[str(sequence)];frames=entry['frames'];total=entry['duration']
        selected=math_node('COMPARE',attribute('sheet_sequence'),sequence)
        rate=animation_rate(renderer)
        if renderer.get('animation_fit_lifetime',False):time=math_node('MULTIPLY',fraction,total)
        else:
            multiplier=rate*total/len(frames) if renderer.get('use animation rate as FPS',False) else rate*total
            time=math_node('MULTIPLY',age,multiplier)
        if entry['clamp']:time=math_node('MINIMUM',time,total)
        else:time=math_node('MODULO',time,total)
        start=0.
        for index,frame in enumerate(frames):
            end=start+frame['duration']
            mask=selected
            if len(frames)>1:
                lower=math_node('SUBTRACT',1,math_node('LESS_THAN',time,start))
                upper=math_node('LESS_THAN',time,end) if index<len(frames)-1 else 1
                mask=math_node('MULTIPLY',selected,math_node('MULTIPLY',lower,upper))
            for component,value in enumerate(frame['coordinates'][0]):
                rectangle[component]=math_node('ADD',rectangle[component],math_node('MULTIPLY',mask,value))
            start=end
    left,top,right,bottom=rectangle
    u=math_node('ADD',left,math_node('MULTIPLY',attribute('uv_u'),math_node('SUBTRACT',right,left)))
    v=math_node('ADD',math_node('SUBTRACT',1,bottom),math_node('MULTIPLY',attribute('uv_v'),math_node('SUBTRACT',bottom,top)))
    vector=nodes.new('ShaderNodeCombineXYZ');links.new(u,vector.inputs['X']);links.new(v,vector.inputs['Y'])
    store=nodes.new('GeometryNodeStoreNamedAttribute');store.data_type='FLOAT_VECTOR';store.domain='CORNER';store.inputs['Name'].default_value='sfm_particle_uv'
    links.new(geometry,store.inputs['Geometry']);links.new(vector.outputs['Vector'],store.inputs['Value'])
    return store.outputs['Geometry']
