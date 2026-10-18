"""Decode Source face lightmaps without conflating HDR and LDR offsets.

This data layer preserves all styles and directional blocks. Rendering those
blocks requires a separate material/UV binding; decoding alone is not lighting.
"""
import numpy as np


def select_lighting(bsp):
    from SourceIO.library.source1.bsp.lumps.face_lump import HDRFaceLump
    from SourceIO.library.source1.bsp.lumps.lightmap_lump import LightmapDataHDRLump
    ordinary=bsp.get_lump('LUMP_FACES').faces
    for mode,face_name,light_name in (
        ('HDR','LUMP_FACES_HDR','LUMP_LIGHTING_HDR'),
        ('LDR','LUMP_FACES','LUMP_LIGHTING')):
        face_lump=bsp.get_lump(face_name);lighting=bsp.get_lump(light_name)
        if face_lump is None or lighting is None or not len(lighting.lightmap_data):continue
        faces=face_lump.faces
        # Source permits different HDR faces. Existing mesh provenance indexes
        # the ordinary table, so reject an incompatible table rather than guess.
        if len(faces)!=len(ordinary) or any(
            (a.first_edge,a.edge_count,a.plane_index,a.tex_info_id,a.disp_info_id)!=
            (b.first_edge,b.edge_count,b.plane_index,b.tex_info_id,b.disp_info_id)
            for a,b in zip(faces,ordinary)):
            continue
        return mode,faces,lighting.lightmap_data
    return None,ordinary,None


def decode_face(face,texture_info,samples):
    """Return style -> (base, three bump directions if present), linear RGB.

    Face sizes omit the inclusive last luxel. Offsets are bytes, samples RGBe.
    A malformed range raises instead of reading another face's lightmap.
    """
    if face.light_offset<0:return {}
    width=int(face.lightmap_width)+1;height=int(face.lightmap_height)+1
    styles=[]
    for style in face.styles:
        style=int(style)&255
        if style==255:break
        styles.append(style)
    if width<=0 or height<=0 or not styles:return {}
    blocks=4 if int(texture_info.flags)&0x800 else 1
    count=width*height*blocks*len(styles)
    start=int(face.light_offset)//4
    if face.light_offset%4 or start<0 or start+count>len(samples):
        raise ValueError('BSP face lightmap sample range is invalid')
    data=samples[start:start+count]
    exponent=np.exp2(data['e'].astype(np.float32).reshape(-1))
    rgb=np.stack([data[c].reshape(-1) for c in ('r','g','b')],axis=-1).astype(np.float32)
    rgb*=exponent[:,None]/255.
    rgb=rgb.reshape(len(styles),blocks,height,width,3)
    return {style:rgb[index] for index,style in enumerate(styles)}


def atlas_tiles(tiles,page_size=1024):
    """Shelf-pack RGB face tiles, with duplicated borders and a black fallback."""
    pages=[];placements={};page=None;x=y=2;row_height=0
    for face_id,tile in sorted(tiles.items(),key=lambda item:-item[1].shape[0]):
        height,width=tile.shape[:2];padded_w=width+2;padded_h=height+2
        if max(padded_w,padded_h)>page_size-2:
            raise ValueError('BSP face exceeds lightmap atlas page size')
        if page is None or y+padded_h>page_size:
            page=np.zeros((page_size,page_size,4),dtype=np.float32);page[:,:,3]=1
            pages.append(page);x=y=2;row_height=0
        if x+padded_w>page_size:
            x=2;y+=row_height;row_height=0
            if y+padded_h>page_size:
                page=np.zeros((page_size,page_size,4),dtype=np.float32);page[:,:,3]=1
                pages.append(page);x=y=2
        page[y:y+padded_h,x:x+padded_w,:3]=np.pad(tile,((1,1),(1,1),(0,0)),mode='edge')
        placements[face_id]=(len(pages)-1,x+1,y+1,width,height)
        x+=padded_w;row_height=max(row_height,padded_h)
    return pages,placements


def directional_color(tree,surface,images,uv,material):
    """SDK normalized squared bump-basis weights, evaluated in tangent space."""
    normal=surface.inputs['Normal']
    if not normal.is_linked:return None
    normal_map=normal.links[0].from_node
    if normal_map.type!='NORMAL_MAP' or normal_map.space!='TANGENT':return None
    color=normal_map.inputs['Color']
    if not color.is_linked:return None
    # SourceIO inverts the green channel for Blender. Undo it when recovering
    # the Source tangent-space vector; do not use a world-space shading normal.
    signed=tree.nodes.new('ShaderNodeVectorMath');signed.operation='MULTIPLY'
    tree.links.new(color.links[0].from_socket,signed.inputs[0]);signed.inputs[1].default_value=(2,-2,2)
    offset=tree.nodes.new('ShaderNodeVectorMath');offset.operation='ADD'
    tree.links.new(signed.outputs[0],offset.inputs[0]);offset.inputs[1].default_value=(-1,1,-1)
    basis=((.8164966106414795,0,.5773502588272095),(-.4082482159137726,.7071067690849304,.5773502588272095),(-.4082482159137726,-.7071067690849304,.5773502588272095))
    ssbump=bool(material.get('sfm_lightmap_ssbump'))
    if ssbump:
        # SourceIO's SSBump-to-normal conversion is an affine transform, with
        # no normalization. Invert that exact matrix to recover the three
        # original directional visibility channels, including texture blends.
        basis=np.linalg.inv(np.array(((.81649661064147949,-.40824833512306213,-.40824833512306213),(0,.70710676908493042,-.7071068286895752),(.57735025882720947,.57735025882720947,.57735025882720947))))
    weights=[];terms=[]
    for index,vector in enumerate(basis):
        dot=tree.nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT'
        tree.links.new(offset.outputs[0],dot.inputs[0]);dot.inputs[1].default_value=vector
        weight=dot.outputs['Value']
        if not ssbump:
            clamp=tree.nodes.new('ShaderNodeClamp');tree.links.new(weight,clamp.inputs['Value'])
            square=tree.nodes.new('ShaderNodeMath');square.operation='MULTIPLY'
            tree.links.new(clamp.outputs[0],square.inputs[0]);tree.links.new(clamp.outputs[0],square.inputs[1]);weight=square.outputs[0]
        weights.append(weight)
        texture=tree.nodes.new('ShaderNodeTexImage');texture.image=images[index+1];texture.interpolation='Linear';texture.extension='EXTEND'
        texture.name=f'SFM directional lightmap {index+1}';tree.links.new(uv.outputs[0],texture.inputs['Vector'])
        term=tree.nodes.new('ShaderNodeMixRGB');term.blend_type='MULTIPLY';term.inputs[0].default_value=1
        tree.links.new(texture.outputs['Color'],term.inputs[1]);tree.links.new(weight,term.inputs[2]);terms.append(term.outputs[0])
    total=weights[0];summed=terms[0]
    for weight,term in zip(weights[1:],terms[1:]):
        add=tree.nodes.new('ShaderNodeMath');add.operation='ADD';tree.links.new(total,add.inputs[0]);tree.links.new(weight,add.inputs[1]);total=add.outputs[0]
        add_color=tree.nodes.new('ShaderNodeMixRGB');add_color.blend_type='ADD';add_color.inputs[0].default_value=1
        tree.links.new(summed,add_color.inputs[1]);tree.links.new(term,add_color.inputs[2]);summed=add_color.outputs[0]
    material['sfm_directional_lightmap']=True
    if ssbump:
        material['sfm_ssbump_lightmap']=True
        return summed
    divide=tree.nodes.new('ShaderNodeMixRGB');divide.blend_type='DIVIDE';divide.inputs[0].default_value=1
    tree.links.new(summed,divide.inputs[1]);tree.links.new(total,divide.inputs[2])
    return divide.outputs[0]


def preserve_strength_animation(tree,strength):
    """Move a keyed mask off the emission strength that becomes constant one."""
    if strength.is_linked:return strength.links[0].from_socket
    animation=tree.animation_data
    if not animation:return None
    old_path=strength.path_from_id('default_value')
    curves=[]
    if animation.action:
        for layer in animation.action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:curves.extend(bag.fcurves)
    drivers=[curve for curve in animation.drivers if curve.data_path==old_path]
    if not any(curve.data_path==old_path for curve in curves) and not drivers:return None
    node=tree.nodes.new('ShaderNodeValue');node.name='SFM original emission mask'
    node.outputs[0].default_value=strength.default_value
    new_path=node.outputs[0].path_from_id('default_value')
    if animation.action:
        old_slot=animation.action_slot
        action=animation.action.copy();animation.action=action
        animation.action_slot=next(slot for slot in action.slots if slot.identifier==old_slot.identifier)
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        if curve.data_path==old_path:curve.data_path=new_path
    for curve in drivers:curve.data_path=new_path
    return node.outputs[0]


def bind_material(material,image,directional_images=None,vertex_attribute=None):
    """Add baked diffuse illumination to native Principled surfaces."""
    tree=material.node_tree
    surfaces=[node for node in tree.nodes if node.type=='BSDF_PRINCIPLED'] if tree else []
    if not surfaces:return False
    uv=None
    if vertex_attribute:
        texture=tree.nodes.new('ShaderNodeVertexColor');texture.layer_name=vertex_attribute
        texture.name='SFM baked prop lighting'
    else:
        uv=tree.nodes.new('ShaderNodeUVMap');uv.uv_map='SFM Lightmap'
        texture=tree.nodes.new('ShaderNodeTexImage');texture.image=image
        texture.name='SFM baked lightmap';texture.interpolation='Linear';texture.extension='EXTEND'
        tree.links.new(uv.outputs['UV'],texture.inputs['Vector'])
    for surface in surfaces:
        multiply=tree.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
        base=surface.inputs['Base Color']
        if base.is_linked:tree.links.new(base.links[0].from_socket,multiply.inputs[1])
        else:multiply.inputs[1].default_value=base.default_value
        lighting=directional_color(tree,surface,directional_images,uv,material) if directional_images else None
        tree.links.new(lighting or texture.outputs['Color'],multiply.inputs[2])
        color=surface.inputs['Emission Color'];strength=surface.inputs['Emission Strength']
        strength_source=preserve_strength_animation(tree,strength)
        # Retain pre-existing self illumination and its strength.
        existing=tree.nodes.new('ShaderNodeMixRGB');existing.blend_type='MULTIPLY';existing.inputs[0].default_value=1
        if color.is_linked:tree.links.new(color.links[0].from_socket,existing.inputs[1])
        else:existing.inputs[1].default_value=color.default_value
        if strength_source:tree.links.new(strength_source,existing.inputs[2])
        else:existing.inputs[2].default_value=(strength.default_value,)*3+(1,)
        baked=multiply.outputs[0]
        if material.get('sfm_lightmap_selfillum'):
            # SDK lerp(baked_diffuse, selfillum_tint*albedo, alpha). The
            # pre-existing emission strength is SourceIO's selfillum mask.
            inverse=tree.nodes.new('ShaderNodeMath');inverse.operation='SUBTRACT';inverse.inputs[0].default_value=1
            if strength_source:tree.links.new(strength_source,inverse.inputs[1])
            else:inverse.inputs[1].default_value=strength.default_value
            masked=tree.nodes.new('ShaderNodeMixRGB');masked.blend_type='MULTIPLY';masked.inputs[0].default_value=1
            tree.links.new(baked,masked.inputs[1]);tree.links.new(inverse.outputs[0],masked.inputs[2]);baked=masked.outputs[0]
            diffuse=tree.nodes.new('ShaderNodeMixRGB');diffuse.blend_type='MULTIPLY';diffuse.inputs[0].default_value=1
            if base.is_linked:tree.links.new(base.links[0].from_socket,diffuse.inputs[1])
            else:diffuse.inputs[1].default_value=base.default_value
            tree.links.new(inverse.outputs[0],diffuse.inputs[2]);tree.links.new(diffuse.outputs[0],base)
            material['sfm_lightmap_selfillum_blended']=True
        add=tree.nodes.new('ShaderNodeMixRGB');add.blend_type='ADD';add.inputs[0].default_value=1
        tree.links.new(existing.outputs[0],add.inputs[1]);tree.links.new(baked,add.inputs[2])
        tree.links.new(add.outputs[0],color)
        for link in list(strength.links):tree.links.remove(link)
        strength.default_value=1
    if vertex_attribute:material['sfm_baked_prop_lighting']=vertex_attribute
    else:material['sfm_baked_lightmap']=image.name
    return True


def apply(bsp,objects,scale):
    import bpy
    mode,faces,samples=select_lighting(bsp)
    record={'mode':mode,'meshes':0,'faces':0,'atlases':0,'unsupported_materials':[],
            'bump_faces_using_base_block':0,'directional_mesh_faces':0,'additional_styles':[],'render_equivalence_verified':False}
    if samples is None:return record
    textures=bsp.get_lump('LUMP_TEXINFO').texture_info
    meshes=[obj for obj in objects if obj.type=='MESH' and obj.data.attributes.get('sfm_bsp_face_id')]
    used={int(entry.value) for obj in meshes for entry in obj.data.attributes['sfm_bsp_face_id'].data}
    tiles={};styles=set();bump_tiles={}
    for index in used:
        face=faces[index];decoded=decode_face(face,textures[face.tex_info_id],samples)
        if not decoded:continue
        styles.update(style for style in decoded if style!=0)
        # Static style zero is the benchmark maps' baked lighting. Other styles
        # require their Source runtime pattern and must not be guessed/summed.
        if 0 not in decoded:continue
        tiles[index]=decoded[0][0]
        if decoded[0].shape[0]>1:bump_tiles[index]=decoded[0][1:]
    pages,placements=atlas_tiles(tiles)
    images=[]
    for index,pixels in enumerate(pages):
        image=bpy.data.images.new(f'{bsp.filepath.stem} SFM lightmap {index}',width=pixels.shape[1],height=pixels.shape[0],float_buffer=True)
        image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(pixels.ravel())
        image.file_format='OPEN_EXR';image.pack();images.append(image)
    directional={}
    for page in {placements[index][0] for index in bump_tiles}:
        page_images=[images[page]]
        for direction in range(3):
            pixels=np.zeros_like(pages[page]);pixels[:,:,3]=1
            for face_id,blocks in bump_tiles.items():
                tile_page,x,y,width,height=placements[face_id]
                if tile_page!=page:continue
                pixels[y-1:y+height+1,x-1:x+width+1,:3]=np.pad(blocks[direction],((1,1),(1,1),(0,0)),mode='edge')
            image=bpy.data.images.new(f'{bsp.filepath.stem} SFM lightmap {page} direction {direction+1}',width=pixels.shape[1],height=pixels.shape[0],float_buffer=True)
            image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(pixels.ravel());image.file_format='OPEN_EXR';image.pack();page_images.append(image)
        directional[page]=page_images
    materials={}
    for obj in meshes:
        mesh=obj.data;attribute=mesh.attributes['sfm_bsp_face_id']
        raw=mesh.uv_layers.get('sfm_lightmap_luxels')
        uv=mesh.uv_layers.get('SFM Lightmap') or mesh.uv_layers.new(name='SFM Lightmap')
        original=list(mesh.materials)
        for polygon in mesh.polygons:
            face_id=int(attribute.data[polygon.index].value);placement=placements.get(face_id)
            if placement is None:continue
            page,x,y,width,height=placement;face=faces[face_id]
            vectors=np.asarray(textures[face.tex_info_id].lightmap_vectors)
            for loop_index in polygon.loop_indices:
                if raw:luxels=np.array(raw.data[loop_index].uv)
                else:
                    position=np.array(mesh.vertices[mesh.loops[loop_index].vertex_index].co)/scale
                    luxels=vectors[:,:3]@position+vectors[:,3]-np.asarray(face.lightmap_texture_mins_in_luxels)
                # Constant-light faces have zero-sized lightmaps despite larger
                # geometry. Clamp the coordinates to the valid Source tile.
                luxels=np.clip(luxels,(0,0),(width-1,height-1))
                uv.data[loop_index].uv=((luxels[0]+x+.5)/pages[page].shape[1],(luxels[1]+y+.5)/pages[page].shape[0])
            if polygon.material_index>=len(original):continue
            source=original[polygon.material_index]
            if source is None:continue
            is_bump=face_id in bump_tiles
            key=(source,page,is_bump)
            if key not in materials:
                converted=source.copy();converted.name=source.name+' SFM lightmap'
                if bind_material(converted,images[page],directional.get(page) if is_bump else None):materials[key]=converted
                else:
                    record['unsupported_materials'].append(source.name);materials[key]=None
                    bpy.data.materials.remove(converted)
            converted=materials[key]
            if converted is None:continue
            slot=next((i for i,m in enumerate(mesh.materials) if m==converted),None)
            if slot is None:slot=len(mesh.materials);mesh.materials.append(converted)
            polygon.material_index=slot;record['faces']+=1
            if is_bump:
                if converted.get('sfm_directional_lightmap'):record['directional_mesh_faces']+=1
                else:record['bump_faces_using_base_block']+=1
        record['meshes']+=1
    record['atlases']=len(images);record['additional_styles']=sorted(styles)
    record['unsupported_materials']=sorted(set(record['unsupported_materials']))
    return record
