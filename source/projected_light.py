"""Perspective cookie coordinates for native Cycles spotlights."""
import math

def enclosing_cone(horizontal,vertical):
    return 2*math.atan(math.hypot(math.tan(math.radians(horizontal)/2),math.tan(math.radians(vertical)/2)))

def nodes(light,image,horizontal=45,vertical=45):
    light.spot_size=enclosing_cone(horizontal,vertical);light.spot_blend=0
    light.use_nodes=True
    tree=light.node_tree;tree.nodes.clear()
    output=tree.nodes.new('ShaderNodeOutputLight')
    emission=tree.nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
    tree.links.new(emission.outputs[0],output.inputs['Surface'])
    coordinate=tree.nodes.new('ShaderNodeTexCoord')
    split=tree.nodes.new('ShaderNodeSeparateXYZ');tree.links.new(coordinate.outputs['Normal'],split.inputs[0])
    combine=tree.nodes.new('ShaderNodeCombineXYZ')
    scales=[]
    for component,fov in (('X',horizontal),('Y',vertical)):
        divide=tree.nodes.new('ShaderNodeMath');divide.operation='DIVIDE'
        tree.links.new(split.outputs[component],divide.inputs[0]);tree.links.new(split.outputs['Z'],divide.inputs[1])
        scale=tree.nodes.new('ShaderNodeMath');scale.operation='MULTIPLY_ADD'
        scale.inputs[1].default_value=-1/(2*math.tan(math.radians(fov)/2));scale.inputs[2].default_value=.5
        tree.links.new(divide.outputs[0],scale.inputs[0]);tree.links.new(scale.outputs[0],combine.inputs[component]);scales.append(scale)
    combine.name='SFM projected cookie coordinates'
    if image is None:
        texture=tree.nodes.new('ShaderNodeRGB');texture.outputs[0].default_value=(1,1,1,1)
    else:
        texture=tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.extension='CLIP'
        tree.links.new(combine.outputs[0],texture.inputs['Vector'])
    texture.name='SFM projected texture base'
    tree.links.new(texture.outputs['Color'],emission.inputs['Color'])
    return scales

def load_cookie(assets,path):
    path=path.removeprefix('materials/');path=path.rsplit('.',1)[0] if path.endswith(('.vtf','.vmt')) else path
    buffer=assets.buffer('materials/'+path+'.vtf')
    if buffer is None:
        from SourceIO.library.source1.vmt import VMT
        source=assets.buffer('materials/'+path+'.vmt')
        if source is None:raise FileNotFoundError('Projected texture '+path)
        material=VMT(source,assets.TinyPath('materials/'+path+'.vmt'),assets.cm)
        path=material.get_string('$basetexture','').replace('\\','/').removeprefix('materials/').removesuffix('.vtf')
        buffer=assets.buffer('materials/'+path+'.vtf')
        if buffer is None:raise FileNotFoundError('Projected base texture '+path)
    from SourceIO.blender_bindings.source1.vtf import import_texture
    image=import_texture(assets.TinyPath(path),buffer);image.pack()
    return image,path

def selection(light,images,paths,frames,curves):
    tree=light.node_tree
    first=tree.nodes['SFM projected texture base']
    vector=tree.nodes['SFM projected cookie coordinates'].outputs[0]
    emission=next(n for n in tree.nodes if n.type=='EMISSION')
    color=first.outputs['Color']
    for path,image in list(images.items())[1:]:
        if image is None:
            texture=tree.nodes.new('ShaderNodeRGB');texture.outputs[0].default_value=(1,1,1,1)
        else:
            texture=tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.extension='CLIP'
            tree.links.new(vector,texture.inputs['Vector'])
        mix=tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX'
        tree.links.new(color,mix.inputs[1]);tree.links.new(texture.outputs['Color'],mix.inputs[2])
        curves.add(mix.inputs[0].path_from_id('default_value'),frames,[float(value==path) for value in paths],interpolation='CONSTANT')
        color=mix.outputs[0]
    tree.links.new(color,emission.inputs['Color'])

def import_cookie(assets,shot,element,light,frames,seconds,Curves):
    paths=[str(shot.value(element,'texture',t,'')).replace('\\','/').strip() for t in seconds]
    if not any(paths):return None
    images={};resolved=[]
    for path in dict.fromkeys(paths):
        if not path:images[path]=None;resolved.append('');continue
        image,source=load_cookie(assets,path);images[path]=image;resolved.append(source)
    image=next(iter(images.values()))
    fovs=[[max(1.,min(179.,float(shot.value(element,key,t,45.)))) for t in seconds] for key in ('horizontalFOV','verticalFOV')]
    untextured_blend=light.spot_blend
    scales=nodes(light,image,fovs[0][0],fovs[1][0])
    curves=Curves(light.node_tree,element.name+' projected texture')
    selection(light,images,paths,frames,curves)
    for node,values in zip(scales,fovs):
        curves.add(node.inputs[1].path_from_id('default_value'),frames,[-1/(2*math.tan(math.radians(v)/2)) for v in values])
    light_curves=Curves(light,element.name+' light properties',reuse=True)
    for curve in list(light_curves.bag.fcurves):
        if curve.data_path=='spot_size':light_curves.bag.fcurves.remove(curve)
    light_curves.add('spot_size',frames,[enclosing_cone(h,v) if path else math.radians(h) for h,v,path in zip(*fovs,paths)])
    light_curves.add('spot_blend',frames,[0. if path else untextured_blend for path in paths],interpolation='CONSTANT')
    light['sfm_projected_texture']=next(source for source in resolved if source)
    light['sfm_projected_textures']=resolved
    return light['sfm_projected_texture']
