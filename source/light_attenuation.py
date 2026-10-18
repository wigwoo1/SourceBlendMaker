"""Source flashlight attenuation in native Cycles light nodes.

The distance polynomial follows Valve's common_flashlight_fxc.h. LightFalloff
Constant cancels Cycles' inverse-square factor before the Source polynomial.
Absolute renderer brightness, shadow attenuation and clipping remain separate.
"""
def apply(light,shot,element,frames,seconds,Curves,scale=.0254):
    light.use_nodes=True;tree=light.node_tree
    emission=next((node for node in tree.nodes if node.type=='EMISSION'),None)
    if emission is None:raise ValueError('Light has no emission shader for attenuation')
    curves=Curves(tree,element.name+' attenuation',reuse=True)
    def math_node(operation,a,b=None):
        node=tree.nodes.new('ShaderNodeMath');node.operation=operation
        for index,value in enumerate((a,b)):
            if value is None:continue
            if isinstance(value,(int,float)):node.inputs[index].default_value=value
            else:tree.links.new(value,node.inputs[index])
        return node.outputs[0]
    path=tree.nodes.new('ShaderNodeLightPath');path.name='SFM light distance'
    distance=math_node('MAXIMUM',path.outputs['Ray Length'],1e-6)
    source_distance=math_node('DIVIDE',distance,scale)
    inverse=math_node('DIVIDE',1.,source_distance)
    inverse_square=math_node('MULTIPLY',inverse,inverse)
    terms=[];settings={}
    for name,default,factor in (('constantAttenuation',0.,None),('linearAttenuation',0.,inverse),('quadraticAttenuation',1500.,inverse_square)):
        values=[float(shot.value(element,name,time,default)) for time in seconds]
        node=tree.nodes.new('ShaderNodeValue');node.name='SFM '+name;node.outputs[0].default_value=values[0]
        curves.add(node.outputs[0].path_from_id('default_value'),frames,values)
        terms.append(node.outputs[0] if factor is None else math_node('MULTIPLY',node.outputs[0],factor))
        settings[name]={'minimum':min(values),'maximum':max(values)}
    total=math_node('ADD',math_node('ADD',terms[0],terms[1]),terms[2])
    attenuation=math_node('MINIMUM',math_node('MAXIMUM',total,0.),1.)
    falloff=tree.nodes.new('ShaderNodeLightFalloff');falloff.name='SFM cancel inverse square';falloff.inputs['Strength'].default_value=1.
    strength=math_node('MULTIPLY',falloff.outputs['Constant'],attenuation)
    previous=emission.inputs['Strength']
    if previous.is_linked:strength=math_node('MULTIPLY',strength,previous.links[0].from_socket)
    elif previous.default_value!=1.:strength=math_node('MULTIPLY',strength,float(previous.default_value))
    tree.links.new(strength,previous)
    light['sfm_attenuation_polynomial']=True
    return {'light':element.name,'parameters':settings,'source_distance_scale':scale,
            'formula':'clamp(c + l / distance + q / distance_squared, 0, 1)',
            'native_cycles_nodes':True,'source_absolute_brightness_verified':False,
            'source_near_far_clipping_and_shadow_fade_verified':False}
