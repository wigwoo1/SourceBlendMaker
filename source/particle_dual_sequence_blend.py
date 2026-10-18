"""Decoded SpriteCard two-sequence blend stage for supported materials.

Inputs are the separately sampled/interpolated texture sequences. Vertex tint,
overbright, depth/screen fades, atlas playback and zoom are separate stages.
"""
import math


def _mode(mode):
    if isinstance(mode,bool) or mode not in (0,1,2):
        raise ValueError('SpriteCard sequence blend mode must be 0, 1 or 2')
    return int(mode)


def combine(primary,secondary,mode):
    mode=_mode(mode)
    if any(len(v)!=4 or not all(math.isfinite(float(x)) for x in v)
           or not 0<=v[3]<=1 for v in (primary,secondary)):
        raise ValueError('Sequence samples require finite RGBA with normalized alpha')
    if mode==0:return tuple((a+b)*.5 for a,b in zip(primary,secondary))
    if mode==1:return (*secondary[:3],primary[3])
    alpha=secondary[3]
    return (*(a+(b-a)*alpha for a,b in zip(primary[:3],secondary[:3])),primary[3])


def create_group(mode):
    import bpy
    mode=_mode(mode)
    group=bpy.data.node_groups.new('SFM dual-sequence blend '+str(mode),'ShaderNodeTree')
    group['sfm_blend_stage']='Decoded pixel blend; supported dual-sequence UV/table/zoom path'
    group['sfm_sequence_blend_mode']=mode
    for name,socket in (('Primary Color','NodeSocketColor'),('Primary Alpha','NodeSocketFloat'),
                        ('Secondary Color','NodeSocketColor'),('Secondary Alpha','NodeSocketFloat')):
        group.interface.new_socket(name=name,in_out='INPUT',socket_type=socket)
    group.interface.new_socket(name='Color',in_out='OUTPUT',socket_type='NodeSocketColor')
    group.interface.new_socket(name='Alpha',in_out='OUTPUT',socket_type='NodeSocketFloat')
    nodes,links=group.nodes,group.links
    incoming=nodes.new('NodeGroupInput');outgoing=nodes.new('NodeGroupOutput')
    if mode==1:
        color=incoming.outputs['Secondary Color']
    else:
        mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.use_clamp=False
        links.new(incoming.outputs['Primary Color'],mix.inputs[1])
        links.new(incoming.outputs['Secondary Color'],mix.inputs[2])
        if mode==0:mix.inputs[0].default_value=.5
        else:links.new(incoming.outputs['Secondary Alpha'],mix.inputs[0])
        color=mix.outputs[0]
    alpha=incoming.outputs['Primary Alpha']
    if mode==0:
        add=nodes.new('ShaderNodeMath');add.operation='ADD'
        links.new(alpha,add.inputs[0]);links.new(incoming.outputs['Secondary Alpha'],add.inputs[1])
        half=nodes.new('ShaderNodeMath');half.operation='MULTIPLY';half.inputs[1].default_value=.5
        links.new(add.outputs[0],half.inputs[0]);alpha=half.outputs[0]
    links.new(color,outgoing.inputs['Color']);links.new(alpha,outgoing.inputs['Alpha'])
    return group
