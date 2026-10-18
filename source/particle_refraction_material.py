"""Experimental native Refract material; production routing remains disabled.

Normal/alpha displacement, tint and cyclic AnimatedTexture proxies are connected.
The experimental scene compositor applies blur and independent ordered layers.
Secondary normals, shot phase and exact Source visual parity remain unverified.
"""
def create(assets,path,scene=None,time_offset=0):
    import bpy,json
    from particles import material_path
    from SourceIO.library.source1.vmt import VMT
    from SourceIO.library.source1.vtf import load_texture,load_texture_frames
    from SourceIO.library.utils import MemoryBuffer
    from particle_sheet import parse_vtf
    from particle_refraction import dx9_blur_amount
    from particle_refraction_nodes import normal_displacement,write_passes,write_tint
    path='materials/'+material_path(path)
    buffer=assets.buffer(path)
    if buffer is None:raise FileNotFoundError(path)
    vmt=VMT(buffer,assets.TinyPath(path),assets.cm)
    if vmt.shader.lower()!='refract':raise ValueError('Experimental material requires Refract')
    texture=vmt.get_string('$normalmap','').replace('\\','/')
    if not texture:raise ValueError('Refraction material has no normal map')
    if not texture.startswith('materials/'):texture='materials/'+texture
    if not texture.lower().endswith('.vtf'):texture+='.vtf'
    source=assets.buffer(texture)
    if source is None:raise FileNotFoundError(texture)
    raw=source.read();sheet=parse_vtf(raw)
    frames,height,width=load_texture_frames(MemoryBuffer(raw))
    bump_frame=vmt.get_int('$bumpframe',0)
    if not frames or not 0<=bump_frame<len(frames):raise ValueError('Normal-map frame unavailable: '+str(bump_frame))
    rgba=frames[bump_frame]
    image=bpy.data.images.new(texture+' refraction data',width=width,height=height,alpha=True,float_buffer=True)
    image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(rgba.ravel());image.pack()
    material=bpy.data.materials.new(path+' experimental refraction');material.use_nodes=True
    material['sfm_particle_material']=path;material['sfm_particle_shader']='Refract'
    material['sfm_particle_sheet']=json.dumps(sheet)
    material['sfm_refraction_experimental']=True
    tint,kind=vmt.get_vector('$refracttint',(1,1,1));tint=list(tint)
    if len(tint)==1:tint*=3
    if kind is int:tint=[v/255 for v in tint]
    material['sfm_refraction_settings']=json.dumps({'amount':vmt.get_float('$refractamount',2),'blur':vmt.get_int('$bluramount',1),'tint':tint,'tint_texture':vmt.get_string('$refracttinttexture',''),'vertex_modulate':bool(vmt.get_int('$vertexcolormodulate',0)),'tint_render_connected':False,'blur_render_connected':False})
    material['sfm_refraction_limitations']='Experimental compositor required; secondary normals, shot timing, multi-effect ordering and exact Source visual parity unverified'
    nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
    offset=normal_displacement(material,image,vmt.get_float('$refractamount',2),bool(vmt.get_int('$vertexcolormodulate',0)))
    write_passes(material,offset)
    normal_node=next(n for n in nodes if n.bl_idname=='ShaderNodeTexImage' and n.image==image)
    color=nodes.new('ShaderNodeRGB');color.outputs[0].default_value=(*tint,1)
    tint_socket=color.outputs[0];coverage=normal_node.outputs['Alpha']
    tint_texture=vmt.get_string('$refracttinttexture','').replace('\\','/')
    if tint_texture:
        if not tint_texture.startswith('materials/'):tint_texture='materials/'+tint_texture
        if not tint_texture.lower().endswith('.vtf'):tint_texture+='.vtf'
        buffer=assets.buffer(tint_texture)
        if buffer is None:raise FileNotFoundError(tint_texture)
        tint_frames,h,w=load_texture_frames(buffer)
        tint_frame=vmt.get_int('$refracttinttextureframe',0)
        if not tint_frames or not 0<=tint_frame<len(tint_frames):raise ValueError('Tint texture frame unavailable: '+str(tint_frame))
        pixels=tint_frames[tint_frame]
        tint_image=bpy.data.images.new(tint_texture+' refraction tint',width=w,height=h,alpha=True,float_buffer=True)
        # Valve's DX9 helper enables sRGB reads for sampler 5 (tint texture).
        # Generated float images store linear pixels; a color-space label alone
        # does not decode the raw VTF values in Blender's shader sampling.
        import numpy as np
        pixels=pixels.copy();rgb=pixels[...,:3]
        pixels[...,:3]=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        tint_image.colorspace_settings.name='Non-Color'
        tint_image.pixels.foreach_set(pixels.ravel());tint_image.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=tint_image
        multiply=nodes.new('ShaderNodeVectorMath');multiply.operation='MULTIPLY'
        links.new(tint_socket,multiply.inputs[0]);links.new(tex.outputs['Color'],multiply.inputs[1])
        double=nodes.new('ShaderNodeVectorMath');double.operation='SCALE';double.inputs['Scale'].default_value=2
        links.new(multiply.outputs[0],double.inputs[0]);tint_socket=double.outputs[0]
    if vmt.get_int('$vertexcolormodulate',0):
        vertex=nodes.new('ShaderNodeVertexColor');vertex.layer_name='sfm_particle_color'
        multiply=nodes.new('ShaderNodeVectorMath');multiply.operation='MULTIPLY'
        links.new(tint_socket,multiply.inputs[0]);links.new(vertex.outputs['Color'],multiply.inputs[1]);tint_socket=multiply.outputs[0]
        alpha=nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY'
        links.new(coverage,alpha.inputs[0]);links.new(vertex.outputs['Alpha'],alpha.inputs[1]);coverage=alpha.outputs[0]
    if vmt.get_int('$fadeoutonsilhouette',1):
        geometry=nodes.new('ShaderNodeNewGeometry')
        dot=nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT'
        links.new(geometry.outputs['Normal'],dot.inputs[0]);links.new(geometry.outputs['Incoming'],dot.inputs[1])
        clamp=nodes.new('ShaderNodeMath');clamp.operation='MAXIMUM';clamp.inputs[1].default_value=0
        links.new(dot.outputs['Value'],clamp.inputs[0])
        power=nodes.new('ShaderNodeMath');power.operation='POWER';power.inputs[1].default_value=3
        links.new(clamp.outputs[0],power.inputs[0])
        fade=nodes.new('ShaderNodeMath');fade.operation='MULTIPLY'
        links.new(coverage,fade.inputs[0]);links.new(power.outputs[0],fade.inputs[1]);coverage=fade.outputs[0]
    write_tint(material,tint_socket,coverage)
    settings=json.loads(material['sfm_refraction_settings']);settings['tint_render_connected']=True;settings['silhouette_fade_connected']=bool(vmt.get_int('$fadeoutonsilhouette',1))
    settings['blur_authored']=settings['blur'];settings['blur']=dx9_blur_amount(settings['blur'])
    settings['normal_frame']=bump_frame;settings['normal_frame_count']=len(frames)
    settings['has_unimplemented_proxies']=bool(vmt.get('proxies',None))
    if tint_texture:
        settings['tint_frame']=tint_frame;settings['tint_frame_count']=len(tint_frames)
    settings['blur_interpretation']='Valve SDK DX9 MAXBLUR=1 clamp; SFM branch parity unverified'
    settings['tint_texture_sampling']='Authored static VTF frame, sRGB tint texture sampling per Valve DX9 sampler 5; animated proxies and whole-pipeline Source parity unverified'
    material['sfm_refraction_settings']=json.dumps(settings)
    from particle_texture_proxy import animations
    from particle_packed_frames import texture_frames
    animated,unsupported=animations(vmt.get('proxies',None))
    for target,rate in animated:
        if target=='$refracttinttexture' and not tint_texture:
            raise ValueError('Animated tint proxy has no tint texture')
        old=normal_node if target=='$normalmap' else tex
        source_frames=frames if target=='$normalmap' else tint_frames
        packed=[]
        for index,pixels in enumerate(source_frames):
            pixels=pixels.copy()
            if target=='$refracttinttexture':
                rgb=pixels[...,:3];pixels[...,:3]=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            h,w=pixels.shape[:2]
            item=bpy.data.images.new(path+target+' frame '+str(index),width=w,height=h,alpha=True,float_buffer=True)
            item.colorspace_settings.name='Non-Color';item.pixels.foreach_set(pixels.ravel());item.pack();packed.append(item)
        color_socket,alpha_socket=texture_frames(material,packed,scene or bpy.context.scene,rate,time_offset=time_offset)
        for link in list(links):
            if link.from_node==old:
                links.new(alpha_socket if link.from_socket.name=='Alpha' else color_socket,link.to_socket)
        nodes.remove(old)
    settings['animated_texture_proxies']=animated
    settings['has_unimplemented_proxies']=bool(unsupported)
    settings['texture_animation_time_offset']=time_offset
    settings['texture_animation_timing']='Scene frame 1 plus explicit Source-time offset; session phase selection unverified'
    settings['authored_shader_features']={'ignore_depth':bool(vmt.get_int('$ignorez',0)),'no_cull':bool(vmt.get_int('$nocull',0)),'secondary_normal':vmt.get_string('$normalmap2',''),'environment_map':vmt.get_string('$envmap','')}
    limitations=[]
    if settings['authored_shader_features']['ignore_depth']:limitations.append('Source $ignorez requires the experimental separate refraction pass; exact Source sorting remains unverified')
    if settings['authored_shader_features']['secondary_normal']:limitations.append('Secondary refraction normal map is preserved as metadata but not sampled')
    if settings['authored_shader_features']['environment_map']:limitations.append('Refraction environment reflection is preserved as metadata but not rendered')
    settings['unsupported_shader_features']=limitations
    if limitations:material['sfm_refraction_limitations']+='; '+'; '.join(limitations)
    material['sfm_refraction_settings']=json.dumps(settings)
    transparent=nodes.new('ShaderNodeBsdfTransparent');out=nodes.new('ShaderNodeOutputMaterial')
    links.new(transparent.outputs[0],out.inputs['Surface'])
    return material

