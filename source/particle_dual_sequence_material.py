"""Compose supported dual sprite sample/blend stages for the ordinary baker.

Max-luminance frame blending, additional textures and material fades are not
implemented here. Inputs are four UV layers and two per-corner float attributes.
"""
from particle_dual_sequence_blend import create_group

UV_NAMES=('sfm_primary_current','sfm_primary_following','sfm_secondary_current','sfm_secondary_following')
BLEND_NAMES=('sfm_primary_blend','sfm_secondary_blend')


def sample_nodes(tree,image,mode,blend_primary=True):
    nodes,links=tree.nodes,tree.links
    samples=[]
    for name in UV_NAMES:
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map=name
        tex=nodes.new('ShaderNodeTexImage');tex.image=image
        links.new(uv.outputs['UV'],tex.inputs['Vector']);samples.append(tex)
    interpolated=[]
    for index,name in enumerate(BLEND_NAMES):
        first,following=samples[index*2:index*2+2]
        if index==0 and not blend_primary:
            interpolated.append((first.outputs['Color'],first.outputs['Alpha']));continue
        blend=nodes.new('ShaderNodeAttribute');blend.attribute_name=name
        mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.use_clamp=False
        links.new(blend.outputs['Fac'],mix.inputs[0])
        links.new(first.outputs['Color'],mix.inputs[1]);links.new(following.outputs['Color'],mix.inputs[2])
        difference=nodes.new('ShaderNodeMath');difference.operation='SUBTRACT'
        links.new(following.outputs['Alpha'],difference.inputs[0]);links.new(first.outputs['Alpha'],difference.inputs[1])
        multiply=nodes.new('ShaderNodeMath');multiply.operation='MULTIPLY'
        links.new(difference.outputs[0],multiply.inputs[0]);links.new(blend.outputs['Fac'],multiply.inputs[1])
        add=nodes.new('ShaderNodeMath');add.operation='ADD'
        links.new(first.outputs['Alpha'],add.inputs[0]);links.new(multiply.outputs[0],add.inputs[1])
        interpolated.append((mix.outputs[0],add.outputs[0]))
    group=nodes.new('ShaderNodeGroup');group.node_tree=create_group(mode)
    for label,(color,alpha) in zip(('Primary','Secondary'),interpolated):
        links.new(color,group.inputs[label+' Color']);links.new(alpha,group.inputs[label+' Alpha'])
    return group.outputs['Color'],group.outputs['Alpha']
