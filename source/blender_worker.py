"""Runs in a private background Blender process; writes native, portable scenes."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import traceback
import time

if hasattr(sys.stdout,'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP))
sys.path.insert(0,str(APP/'vendor'))
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from session import Session,eid,kind,shot_frame_count
from flex import evaluate,target_weight
from audio import envelope
from particles import is_system as is_particle_system
from animation_sampling import parse_target_fps,resample_curve

SCALE=.0254
AXIS=Matrix(((0,0,-1),(-1,0,0),(0,1,0))).to_4x4()
REPORT={'status':'running','errors':[],'warnings':[], 'shots':[], 'assets':[], 'unsupported':[]}


def event(stage,message,progress=None):
    print('SFM_EVENT '+json.dumps({'stage':stage,'message':message,'progress':progress}),flush=True)


def warn(message):
    if message not in REPORT['warnings']:REPORT['warnings'].append(message)


def resolve_pending_materials(assets):
    """Resolve late-created surfaces before auditing and packing their images."""
    from SourceIO.blender_bindings.material_loader.material_loader import ShaderRegistry
    from SourceIO.library.source1.vmt import VMT
    for material in list(bpy.data.materials):
        if not material.get('full_path') or material.get('source_loaded'):continue
        rel=str(material['full_path']).replace('\\','/')
        if not rel.startswith('materials/'):rel='materials/'+rel
        if not rel.endswith('.vmt'):rel+='.vmt'
        buf=assets.buffer(rel);reason='Material file missing' if buf is None else 'Material shader conversion incomplete'
        if buf is not None:
            try:
                vmt=VMT(buf,assets.TinyPath(rel),assets.cm)
                from material_diagnostics import unresolved_reason
                reason=unresolved_reason(vmt)
                ShaderRegistry.source1_create_nodes(assets.cm,material,vmt,{})
            except Exception as exc:reason=str(exc)
        if not material.get('source_loaded'):
            warn(f'Material needs review: {rel}: {reason}')
            REPORT['assets'].append({'type':'material','name':material.name,'path':rel,'converted':False,'reason':reason,'users':material.users})
            if material.users:REPORT['unsupported'].append(f'Material {rel}: {reason}')


def safe_relative(name):
    name=str(name).replace('\\','/').strip('/')
    if ':' in name or any(part=='..' for part in name.split('/')):
        raise ValueError(f'Asset is not a relative Source path: {name}')
    return name


class Assets:
    def __init__(self,job):
        from SourceIO.library.shared.content_manager import ContentManager
        from SourceIO.library.shared.content_manager.providers.source1_gameinfo_provider import Source1GameInfoProvider
        from SourceIO.library.shared.content_manager.providers.loose_files import LooseFilesContentProvider
        from SourceIO.library.shared.content_manager.providers.vpk_provider import VPKContentProvider
        from SourceIO.library.utils import TinyPath
        self.TinyPath=TinyPath
        self.particle_light_gain=float(job.get('particle_light_gain',1.))
        if not 0<self.particle_light_gain<=1000:raise ValueError('Particle glow multiplier must be greater than 0 and at most 1000.')
        self.cm=ContentManager()
        self.root=Path(job['sfm'])
        if (self.root/'game/usermod').is_dir():self.usermod=self.root/'game/usermod'
        elif (self.root/'usermod').is_dir():self.usermod=self.root/'usermod'
        elif (self.root/'gameinfo.txt').is_file():self.usermod=self.root
        else:raise ValueError('SFM folder must contain game/usermod, or select usermod itself.')
        gi=self.usermod/'gameinfo.txt'
        if not gi.is_file():raise FileNotFoundError(f'No gameinfo.txt in {self.usermod}')
        # GameInfoProvider preserves the mounted game's search order internally.
        game_provider=Source1GameInfoProvider(TinyPath(str(gi)))
        self.cm.add_child(game_provider)
        for folder in job.get('extra_assets',[]):
            p=Path(folder)
            if p.suffix.lower()=='.vpk':game_provider._add_mount(VPKContentProvider(TinyPath(str(p))))
            else:
                game_provider._add_mount(LooseFilesContentProvider(TinyPath(str(p))))
                for archive in sorted(p.glob('*_dir.vpk')):
                    game_provider._add_mount(VPKContentProvider(TinyPath(str(archive))))
        self.sidecar=Path(job['output']).with_suffix('.assets')
        self.model_cache={}
        self.missing_models=set()

    def buffer(self,rel):
        return self.cm.find_file(self.TinyPath(safe_relative(rel)))

    def materialize(self,rel):
        rel=safe_relative(rel)
        buf=self.buffer(rel)
        if buf is None:raise FileNotFoundError(rel)
        out=self.sidecar/rel
        out.parent.mkdir(parents=True,exist_ok=True)
        buf.seek(0)
        data=buf.read()
        out.write_bytes(data)
        return out

    def mdl(self,rel):
        if rel in self.model_cache:return self.model_cache[rel]
        if rel in self.missing_models:raise FileNotFoundError(rel)
        from SourceIO.library.models.mdl.v49 import MdlV49
        from SourceIO.library.models.mdl.v44 import MdlV44
        buf=self.buffer(rel)
        if buf is None:
            self.missing_models.add(rel)
            raise FileNotFoundError(rel)
        buf.seek(4);version=buf.read_uint32();buf.seek(0)
        if 45<=version<=49:mdl=MdlV49.from_buffer(buf)
        elif version==44:mdl=MdlV44.from_buffer(buf)
        else:raise ValueError(f'Session model version {version} is not supported yet: {rel}')
        self.model_cache[rel]=mdl
        return mdl


class Curves:
    """Use Blender's action slots so saved files also work without SourceIO."""
    source_fps=0.
    target_fps=0.
    original_animation_keys=0
    written_animation_keys=0
    reduced_animation_curves=0

    @classmethod
    def configure_animation_sampling(cls,source_fps,target_fps):
        cls.source_fps=float(source_fps)
        cls.target_fps=parse_target_fps(target_fps)
        cls.original_animation_keys=0
        cls.written_animation_keys=0
        cls.reduced_animation_curves=0

    @classmethod
    def animation_sampling_report(cls):
        return {'source_fps':cls.source_fps,'requested_keyframe_fps':cls.target_fps or None,
                'effective_keyframe_fps':min(cls.source_fps,cls.target_fps) if cls.target_fps else cls.source_fps,
                'timeline_fps_unchanged':True,'original_keys_on_reduced_curves':cls.original_animation_keys,
                'written_keys_on_reduced_curves':cls.written_animation_keys,
                'curves_reduced':cls.reduced_animation_curves,
                'method':'Retained model-motion and facial keys are linearly interpolated; particles and non-model data are unchanged.'}

    def __init__(self,owner,name,reuse=False):
        self.owner=owner
        ad=owner.animation_data_create()
        if reuse and ad.action:
            self.bag=ad.action.layers[0].strips[0].channelbags[0]
            return
        action=bpy.data.actions.new(name)
        ad=owner.animation_data_create();ad.action=action
        slot=action.slots.new(id_type=owner.id_type,name=owner.name)
        ad.action_slot=slot
        layer=action.layers.new('Animation')
        strip=layer.strips.new(type='KEYFRAME')
        self.bag=strip.channelbags.new(slot=slot)

    def add(self,path,frames,values,interpolation='LINEAR'):
        values=np.asarray(values,dtype=np.float32)
        if values.ndim==1:values=values[:,None]
        frames=np.asarray(frames,dtype=np.float32)
        for index in range(values.shape[1]):
            coordinate_frames=frames;coordinate_values=values[:,index]
            # Test each axis independently: another moving axis must not make
            # a constant coordinate retain thousands of redundant keys.
            if len(frames)>2 and np.allclose(coordinate_values,coordinate_values[0],rtol=0,atol=1e-7):
                coordinate_frames=frames[[0,-1]];coordinate_values=coordinate_values[[0,-1]]
            if getattr(self,'reduce_animation',False) and interpolation!='CONSTANT':
                original_count=len(coordinate_frames)
                coordinate_frames,coordinate_values=resample_curve(coordinate_frames,coordinate_values,self.source_fps,self.target_fps)
                if self.target_fps and self.target_fps<self.source_fps:
                    Curves.original_animation_keys+=original_count
                    Curves.written_animation_keys+=len(coordinate_frames)
                    Curves.reduced_animation_curves+=int(len(coordinate_frames)<original_count)
            existing=self.bag.fcurves.find(path,index=index)
            if existing is not None:self.bag.fcurves.remove(existing)
            fc=self.bag.fcurves.new(data_path=path,index=index)
            fc.keyframe_points.add(len(coordinate_frames))
            fc.keyframe_points.foreach_set('co',np.column_stack((coordinate_frames,coordinate_values)).ravel())
            for point in fc.keyframe_points:point.interpolation=interpolation
            fc.update()


class AnimationCurves(Curves):
    """Curves for model transforms, bones, and facial flexes only."""
    def __init__(self,owner,name,reuse=False):
        super().__init__(owner,name,reuse)
        self.reduce_animation=True


def transform(shot,element,seconds):
    pos=shot.value(element,'position',seconds,(0,0,0))
    rot=shot.value(element,'orientation',seconds,(0,0,0,1))
    scale=shot.value(element,'scale',seconds,1.)
    if isinstance(scale,(int,float)):scale=(scale,)*3
    return Matrix.LocRotScale(Vector(pos)*SCALE,Quaternion((rot[3],rot[0],rot[1],rot[2])),Vector(scale))


def sample_transform(shot,element,frames,seconds,axis=False,rest=None):
    rows=[];previous=None
    constant=hasattr(shot,'is_constant') and all(shot.is_constant(element,attribute) for attribute in ('position','orientation','scale'))
    for t in seconds[:1] if constant else seconds:
        mat=transform(shot,element,t)
        if rest is not None:mat=rest@mat
        if axis:mat=mat@AXIS
        p,q,s=mat.decompose()
        if previous is not None and previous.dot(q)<0:q.negate()
        previous=q.copy()
        rows.append([*p,*q,*s])
    result=np.array(rows)
    return np.repeat(result,len(seconds),axis=0) if constant else result


def animate_transform(obj,shot,element,frames,seconds,axis=False):
    if element is None:return
    rows=sample_transform(shot,element,frames,seconds,axis)
    obj.rotation_mode='QUATERNION'
    obj.location=rows[0,:3];obj.rotation_quaternion=rows[0,3:7];obj.scale=rows[0,7:]
    curves=AnimationCurves(obj,obj.name+' motion')
    curves.add('location',frames,rows[:,:3]);curves.add('rotation_quaternion',frames,rows[:,3:7]);curves.add('scale',frames,rows[:,7:])


def model_variants(container,mdl,gm,shot,frames,seconds):
    """Bake skins/bodygroups as object visibility, sharing geometry and flex keys."""
    skins=[int(shot.value(gm,'skin',t,0)) for t in seconds]
    bodies=[int(shot.value(gm,'body',t,0)) for t in seconds]
    visible=[bool(shot.value(gm,'visible',t,True)) for t in seconds]
    choices=sorted(set(skins))
    body_selection={}
    base=1
    for part in mdl.body_parts:
        # Null models still consume a bodygroup index but produce no mesh.
        indices=[i for i,m in enumerate(part.models) if m.vertex_count>0]
        meshes=container.bodygroups.get(part.name,[])
        for mesh,index in zip(meshes,indices):
            body_selection[mesh.name]=[(body//base)%max(1,len(part.models))==index for body in bodies]
        base*=max(1,len(part.models))
    variants=[]
    for original_mesh in container.objects:
        if original_mesh.type!='MESH':continue
        groups=original_mesh.get('skin_groups',{})
        names=lambda group:[m if isinstance(m,str) else m.name for m in group]
        original_names=names(groups.get('0',[]))
        source_slots=[slot.material for slot in original_mesh.material_slots]
        body_visible=body_selection.get(original_mesh.name,[True]*len(frames))
        for variant,skin in enumerate(choices):
            mesh=original_mesh if variant==0 else original_mesh.copy()
            if variant:
                # Object material slots permit variants to share one mesh and its
                # native shape-key action instead of duplicating vertex data.
                for collection in original_mesh.users_collection:collection.objects.link(mesh)
                mesh.name=original_mesh.name+f' skin {skin}'
            mesh['active_skin']=str(skin)
            variants.append(mesh)
            selected=names(groups.get(str(skin),[]))
            if groups and not selected:warn(f'{original_mesh.name}: unavailable skin {skin}')
            for slot,source in zip(mesh.material_slots,source_slots):
                slot.link='OBJECT'
                material=source
                if source and source.name in original_names and selected:
                    index=original_names.index(source.name)
                    if index<len(selected):material=bpy.data.materials.get(selected[index]) or source
                slot.material=material
            hidden=[not (v and b and active==skin) for v,b,active in zip(visible,body_visible,skins)]
            mesh.hide_render=hidden[0];mesh.hide_viewport=hidden[0]
            if len(set(hidden))>1:
                curves=Curves(mesh,mesh.name+' variant switches')
                curves.add('hide_render',frames,hidden,'CONSTANT')
                curves.add('hide_viewport',frames,hidden,'CONSTANT')
    return variants


def material_overrides(meshes,gm,shot,frames,seconds,assets=None):
    def normalize(name):
        name=str(name).replace('\\','/').lower()
        if name.startswith('materials/'):name=name[10:]
        return name.removesuffix('.vmt')
    from material_proxies import prepare
    overrides,shot,proxy_records,proxy_inputs=prepare(gm,shot,seconds,assets)
    for record in proxy_records:REPORT['assets'].append({'type':'material_color_proxy','model':gm.name,**record})
    for override in overrides:
        keys=[k for k in override.keys() if k!='mtlName']
        texture_keys=('$basetexture','$basetexture2','$bumpmap','$normalmap','$detail','$selfillummask','$phongexponenttexture','$envmapmask','$blendmodulatetexture')
        scalar_keys=('$phongboost','$phongexponent','$rimlightboost','$rimlightexponent')
        supported=[k for k in keys if k.lower() in ('$color','$color2','$alpha','$selfillum','$selfillumtint',*texture_keys,*scalar_keys)]
        unsupported=[k for k in keys if k not in supported and
                     (normalize(override.get('mtlName','')),k.lower()) not in proxy_inputs]
        if unsupported:
            message=f'{gm.name}: unsupported material parameters: {", ".join(unsupported)}'
            warn(message);REPORT['unsupported'].append(message)
        if not supported:continue
        target=normalize(override.get('mtlName',''));copies={};matched=False
        for mesh in meshes:
            for slot in mesh.material_slots:
                original=slot.material
                if original is None:continue
                path=normalize(original.get('full_path',original.name))
                if path!=target and not ('/' not in path and path==target.rsplit('/',1)[-1]):continue
                matched=True
                if original not in copies:
                    material=original.copy();material.name=gm.name+' '+original.name+' override'
                    texture_parameters=[k for k in supported if k.lower() in texture_keys]
                    animated_textures={}
                    if texture_parameters:
                        if assets is None:raise ValueError('Asset resolver is required for texture overrides')
                        from SourceIO.library.source1.vmt import VMT
                        from SourceIO.blender_bindings.material_loader.material_loader import ShaderRegistry
                        path='materials/'+target+'.vmt';buf=assets.buffer(path)
                        if buf is None:raise FileNotFoundError(path)
                        vmt=VMT(buf,assets.TinyPath(path),assets.cm)
                        for key in texture_parameters:
                            values=[str(shot.value(override,key,t,override[key])).replace('\\','/') for t in seconds]
                            if len(set(values))>1:
                                animated_textures[key]=values
                            texture=safe_relative(values[0]);texture=texture.removeprefix('materials/').removesuffix('.vtf')
                            if assets.buffer('materials/'+texture+'.vtf') is None:
                                warn(f'{gm.name}: override texture missing from mounted assets: {texture}; original texture retained')
                                REPORT['unsupported'].append(f'Missing override texture: {texture}')
                                continue
                            vmt.data[key]=texture
                        material['source_loaded']=False;material['full_path']=target
                        ShaderRegistry.source1_create_nodes(assets.cm,material,vmt,{})
                    material.use_nodes=True;tree=material.node_tree
                    shader=next((n for n in tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
                    # Sequential SFM overrides and derived proxy colors must
                    # retain earlier keyed parameters. Isolate the inherited
                    # action before adding curves to this material copy.
                    animation=tree.animation_data
                    if animation and animation.action:
                        old_slot=animation.action_slot
                        animation.action=animation.action.copy()
                        if old_slot:
                            animation.action_slot=next(slot for slot in animation.action.slots if slot.identifier==old_slot.identifier)
                    curves=Curves(tree,material.name+' parameters',reuse=bool(animation and animation.action))
                    if shader is not None and any(k.lower() in ('$selfillum','$selfillumtint') for k in supported):
                        from selfillum import ensure_selfillum
                        ensure_selfillum(material, shader)
                    for key,values in animated_textures.items():
                        from SourceIO.blender_bindings.material_loader.shaders.source1_shader_base import Source1ShaderBase
                        from texture_switch import switch_images
                        nodes=[n for n in tree.nodes if n.type=='TEX_IMAGE' and n.image is not None and
                               (n.name.lower()==key.lower() or n.label.lower()==key.lower())]
                        if not nodes:
                            message=f'{gm.name}: animated texture override {key} has no matching image node'
                            warn(message);REPORT['unsupported'].append(message);continue
                        loader=Source1ShaderBase(assets.cm,vmt)
                        paths=[safe_relative(v).removeprefix('materials/').removesuffix('.vtf') for v in values]
                        unique=list(dict.fromkeys(paths));images=[]
                        for index,path in enumerate(unique):
                            image=loader.load_texture(assets.TinyPath(path))
                            if image is None:
                                message=f'Missing animated override texture: {path}'
                                warn(message);REPORT['unsupported'].append(message)
                                image=nodes[0].image
                            elif index==0:
                                # Preserve the shader loader's conversion of the first image.
                                image=nodes[0].image
                            else:
                                # Data/normal conversions must not change another material's
                                # cached image when an override changes to that same VTF.
                                reference=nodes[0].image
                                image=image.copy()
                                image.name=material.name+' '+key+' '+str(index)
                                if reference.get('ssbump_converted'):
                                    image=loader.convert_ssbump(image)
                                if reference.get('normalmap_converted'):
                                    image=loader.convert_normalmap(image)
                                image.colorspace_settings.name=reference.colorspace_settings.name
                                image.pack()
                            images.append(image)
                        choices=[unique.index(path) for path in paths]
                        for node in nodes:
                            node.image=images[0]
                            switch_images(tree,node,images,choices,frames,curves)
                        REPORT['assets'].append({'type':'animated_material_override','model':gm.name,'parameter':key,'textures':unique})
                    for key in supported:
                        if key in texture_parameters:continue
                        if key.lower() in ('$selfillum','$selfillumtint'):
                            from selfillum import override_socket
                            animated=override_socket(material,shader,key)
                            if animated is None:
                                message=f'{gm.name}: selfillum override shader is unsupported for {target} ({key})'
                                warn(message);REPORT['unsupported'].append(message);continue
                            values=[]
                            for t in seconds:
                                value=shot.value(override,key,t,override[key])
                                if key.lower()=='$selfillum':value=float(float(value)!=0.)
                                else:
                                    from selfillum import color_value
                                    value=color_value(value)
                                values.append(value)
                            animated.default_value=values[0]
                            curves.add(animated.path_from_id('default_value'),frames,values,'CONSTANT' if key.lower()=='$selfillum' else 'LINEAR')
                            continue
                        if key.lower() in scalar_keys:
                            if shader is not None and key.lower()=='$phongexponent':
                                animated=shader.inputs['Roughness']
                                if animated.is_linked:
                                    incoming=animated.links[0].from_node
                                    animated=incoming.inputs.get('B') if incoming.type=='MIX' and incoming.name=='phongmask' else None
                                if animated is not None and not animated.is_linked:
                                    from SourceIO.blender_bindings.material_loader.shaders.source1_shaders.vertexlit_generic import phong_exponent_to_roughness
                                    values=[phong_exponent_to_roughness(float(shot.value(override,key,t,override[key]))) for t in seconds]
                                    animated.default_value=values[0]
                                    curves.add(animated.path_from_id('default_value'),frames,values)
                                    REPORT['assets'].append({'type':'principled_phong_override','model':gm.name,'parameter':key,'approximate':True,'mask_preserved':True})
                                    continue
                            if shader is not None and key.lower()=='$phongboost' and assets is not None:
                                from SourceIO.library.source1.vmt import VMT
                                source_path='materials/'+target+'.vmt';source_buffer=assets.buffer(source_path)
                                if source_buffer is not None:
                                    source_vmt=VMT(source_buffer,assets.TinyPath(source_path),assets.cm)
                                    fresnel=source_vmt.get_vector('$phongfresnelranges',[0,1,1])[0]
                                    factor=max(0.,float(fresnel[1])) if len(fresnel)>1 else 1.
                                    animated=shader.inputs.get('Specular IOR Level') or shader.inputs.get('Specular')
                                    if animated is not None and not animated.is_linked:
                                        def boost_strength(raw):
                                            boost=max(0.,float(raw))
                                            strength=.5*boost if boost<=1 else .5+.5*min(1.,math.log(boost,255.))
                                            return max(0.,min(1.,strength*factor))
                                        values=[boost_strength(shot.value(override,key,t,override[key])) for t in seconds]
                                        animated.default_value=values[0]
                                        curves.add(animated.path_from_id('default_value'),frames,values)
                                        REPORT['assets'].append({'type':'principled_phong_override','model':gm.name,'parameter':key,'approximate':True,'zero_boost_disables_specular':True})
                                        continue
                            animated=next((socket for node in tree.nodes if node.type=='GROUP'
                                           for socket in node.inputs if socket.name.lower().split(' ')[0]==key.lower()
                                           and socket.type=='VALUE'),None)
                            if animated is None or animated.is_linked:
                                message=f'{gm.name}: grouped scalar override is unsupported for {target} ({key})'
                                warn(message);REPORT['unsupported'].append(message);continue
                            values=[float(shot.value(override,key,t,override[key])) for t in seconds]
                            animated.default_value=values[0]
                            curves.add(animated.path_from_id('default_value'),frames,values)
                            continue
                        if key.lower()=='$alpha':
                            if shader is not None:
                                socket=shader.inputs['Alpha'];node=tree.nodes.new('ShaderNodeMath');node.operation='MULTIPLY'
                                node.inputs[0].default_value=socket.default_value
                                if socket.is_linked:tree.links.new(socket.links[0].from_socket,node.inputs[0])
                                tree.links.new(node.outputs[0],socket);animated=node.inputs[1]
                            else:
                                outputs=[n for n in tree.nodes if n.type=='OUTPUT_MATERIAL' and n.inputs['Surface'].is_linked]
                                if not outputs:
                                    message=f'{gm.name}: override shader is unsupported for {target} ({key})'
                                    warn(message);REPORT['unsupported'].append(message);continue
                                transparent=tree.nodes.new('ShaderNodeBsdfTransparent')
                                value=tree.nodes.new('ShaderNodeValue');value.name='SFM override alpha'
                                animated=value.outputs[0]
                                for output in outputs:
                                    surface=output.inputs['Surface'].links[0].from_socket
                                    node=tree.nodes.new('ShaderNodeMixShader')
                                    tree.links.new(animated,node.inputs[0])
                                    tree.links.new(transparent.outputs[0],node.inputs[1])
                                    tree.links.new(surface,node.inputs[2]);tree.links.new(node.outputs[0],output.inputs['Surface'])
                            values=[max(0.,min(1.,float(shot.value(override,key,t,1.)))) for t in seconds]
                        else:
                            if shader is None:
                                animated=next((n.inputs.get('$color2 [RGB field]') for n in tree.nodes
                                               if n.type=='GROUP' and n.inputs.get('$color2 [RGB field]') is not None),None) if key.lower()=='$color2' else None
                                if animated is None:
                                    message=f'{gm.name}: override shader is unsupported for {target} ({key})'
                                    warn(message);REPORT['unsupported'].append(message);continue
                                for link in list(animated.links):tree.links.remove(link)
                            else:
                                socket=shader.inputs['Base Color']
                                incoming=socket.links[0].from_node if socket.is_linked else None
                                if incoming and incoming.type=='MIX_RGB' and incoming.blend_type=='MULTIPLY' and not incoming.inputs[2].is_linked:
                                    animated=incoming.inputs[2]
                                else:
                                    node=tree.nodes.new('ShaderNodeMixRGB');node.blend_type='MULTIPLY';node.inputs[0].default_value=1
                                    node.inputs[1].default_value=socket.default_value
                                    if socket.is_linked:tree.links.new(socket.links[0].from_socket,node.inputs[1])
                                    tree.links.new(node.outputs[0],socket);animated=node.inputs[2]
                                from selfillum import sync_color
                                sync_color(material,shader)
                            values=[]
                            for t in seconds:
                                color=shot.value(override,key,t,(1,1,1))
                                if isinstance(color,(int,float)):color=(color,)*3
                                rgb=list(color)[:3]
                                if type(color).__name__=='Color':rgb=[v/255. for v in rgb]
                                values.append([max(0.,float(v)) for v in rgb]+[1.])
                        animated.default_value=values[0]
                        curves.add(animated.path_from_id('default_value'),frames,values)
                    copies[original]=material
                    REPORT['assets'].append({'type':'material_override','model':gm.name,'material':target,'parameters':supported})
                slot.link='OBJECT';slot.material=copies[original]
        if not matched:
            message=f'{gm.name}: material override target not found: {target}'
            warn(message);REPORT['unsupported'].append(message)


def disable_model_sheen(meshes):
    """User preference: remove sheen from every imported model surface."""
    materials={slot.material for mesh in meshes for slot in mesh.material_slots if slot.material}
    from tile_emission import apply as apply_tile_emission
    apply_tile_emission(materials)
    return disable_material_sheen(materials)


def disable_material_sheen(materials):
    """Also covers late-resolved and nested model shaders."""
    seen=set();count=0
    def visit(tree):
        nonlocal count
        if tree is None or tree in seen:return
        seen.add(tree)
        for node in tree.nodes:
            if node.type=='GROUP':visit(node.node_tree)
            elif node.type=='BSDF_PRINCIPLED':
                weight=node.inputs.get('Sheen Weight')
                if weight is not None:
                    for link in list(weight.links):tree.links.remove(link)
                    weight.default_value=0.;count+=1
    for material in materials:
        visit(material.node_tree)
    return count


def import_model(assets,shot,animset,frames,seconds):
    from SourceIO.blender_bindings.models import import_model as load
    from SourceIO.blender_bindings.models.common import put_into_collections
    from SourceIO.blender_bindings.operators.import_settings_base import ModelOptions
    gm=animset['gameModel'];rel=safe_relative(gm['modelName'])
    event('models',f'Importing {animset.name}: {rel}')
    mdl=assets.mdl(rel)
    options=ModelOptions.default();options.scale=SCALE;options.import_textures=True;options.create_flex_drivers=False
    buf=assets.buffer(rel);buf.seek(0)
    container=load(assets.TinyPath(rel),buf,assets.cm,options)
    if container is None:raise ValueError(f'No model imported for {rel}')
    put_into_collections(container,animset.name,bodygroup_grouping=True)
    root=bpy.data.objects.new(animset.name+' root',None)
    bpy.context.scene.collection.objects.link(root)
    members=list(container.objects)+list(container.attachments)
    if container.armature:members.append(container.armature);container.armature.name=animset.name
    for ob in members:
        if ob.parent is None:ob.parent=root
    animate_transform(root,shot,gm.get('transform'),frames,seconds)
    arm=container.armature
    if arm:
        curves=AnimationCurves(arm,animset.name+' bones')
        matched=0
        session_bones=gm.get('bones',[])
        for bone_index,bt in enumerate(session_bones):
            if bone_index%32==0:
                event('animation',f'{animset.name}: baking bones {bone_index+1}/{len(session_bones)} across {len(frames)} frames')
            match=re.match(r'bone\s+(\d+)\s+\((.*)\)',bt.name)
            bone_name=match.group(2) if match else bt.name
            bone=arm.data.bones.get(bone_name[:63])
            if bone is None:
                warn(f'{animset.name}: unmatched session bone {bone_name}');continue
            rest=bone.matrix_local
            if bone.parent:rest=bone.parent.matrix_local.inverted_safe()@rest
            rows=sample_transform(shot,bt,frames,seconds,rest=rest.inverted_safe())
            pb=arm.pose.bones[bone.name];pb.rotation_mode='QUATERNION'
            curves.add(pb.path_from_id('location'),frames,rows[:,:3])
            curves.add(pb.path_from_id('rotation_quaternion'),frames,rows[:,3:7])
            curves.add(pb.path_from_id('scale'),frames,rows[:,7:]);matched+=1
        REPORT['assets'].append({'type':'model','path':rel,'name':animset.name,'bones':matched})
    else:
        # A compiled static prop can still carry an animated SFM root bone.
        transforms=gm.get('bones',[])
        if transforms:
            pivot=bpy.data.objects.new(animset.name+' static bone',None)
            bpy.context.scene.collection.objects.link(pivot);pivot.parent=root
            for ob in members:
                if ob.parent==root:ob.parent=pivot
            rest=Matrix.LocRotScale(Vector(mdl.bones[0].position)*SCALE,Quaternion((mdl.bones[0].quat[3],*mdl.bones[0].quat[:3])),Vector((1,1,1)))
            pivot['sfm_bone_transform']=eid(transforms[0])
            pivot['sfm_rest_inverse']=[v for row in rest.inverted_safe() for v in row]
            rows=sample_transform(shot,transforms[0],frames,seconds,rest=rest.inverted_safe())
            pivot.rotation_mode='QUATERNION';curves=AnimationCurves(pivot,animset.name+' static bone motion')
            curves.add('location',frames,rows[:,:3]);curves.add('rotation_quaternion',frames,rows[:,3:7]);curves.add('scale',frames,rows[:,7:])
        REPORT['assets'].append({'type':'model','path':rel,'name':animset.name,'bones':len(transforms)})
    meshes=[o for o in container.objects if o.type=='MESH' and o.data.shape_keys]
    if meshes:
        delayed=[];normal_deltas=[]
        for body in mdl.body_parts:
            for model in body.models:
                for part in model.meshes:
                    for flex in part.flexes:
                        vertices=flex.vertex_animations
                        if vertices is None:continue
                        if 'normal_delta' in vertices.dtype.names:
                            count=int(np.count_nonzero(np.any(vertices['normal_delta']!=0,axis=1)))
                            if count:normal_deltas.append({'flex':mdl.flex_names[flex.flex_desc_index],'vertices':count})
                        if 'speed' not in vertices.dtype.names:continue
                        speeds=vertices['speed'].reshape(-1)
                        count=int(np.count_nonzero(speeds<255))
                        if count:delayed.append({'flex':mdl.flex_names[flex.flex_desc_index],'vertices':count,'minimum_speed':int(speeds.min())})
        if normal_deltas:
            REPORT.setdefault('flex_normal_deltas',[]).append({'model':animset.name,'path':rel,'records':normal_deltas,'converted':False})
        if delayed:
            REPORT.setdefault('flex_delayed_vertices',[]).append({'model':animset.name,'path':rel,'records':delayed,'converted':False})
            message=f'{animset.name}: delayed flex vertex history is not baked; current weights are used.'
            warn(message);REPORT['unsupported'].append(message)
        operators=gm.get('globalFlexControllers',[])
        names=gm.get('flexnames',[]);weights=gm.get('flexWeights',[])
        samples=[];range_changes={};unlocked=bool(JOB.get('flex_unlocker',False))
        flex_interval=max(1,len(frames)//10)
        for sample_index,(frame,t) in enumerate(zip(frames,seconds)):
            if sample_index%flex_interval==0:
                event('flex',f'{animset.name}: baking model flex controls, frame {sample_index+1}/{len(frames)}')
            values={n:float(weights[i]) for i,n in enumerate(names) if i<len(weights)}
            for operator in operators:values[operator.name]=float(shot.value(operator,'flexWeight',t,0.))
            for controller in mdl.flex_controllers:
                value=values.get(controller.name,0.)
                if controller.min==controller.max or controller.min<=value<=controller.max:continue
                record=range_changes.setdefault(controller.name,{'name':controller.name,'range':[controller.min,controller.max],
                                                               'raw_min':value,'raw_max':value,'first_blender_frame':int(frame),'clamped_samples':0,'outside_range_samples':0})
                record['raw_min']=min(record['raw_min'],value);record['raw_max']=max(record['raw_max'],value)
                record['outside_range_samples']+=1
                record['clamped_samples']+=int(not unlocked)
            samples.append(evaluate(mdl,values,clamp_controllers=not unlocked))
        if range_changes:
            REPORT.setdefault('flex_range_extrapolation' if unlocked else 'flex_range_clamping',[]).append({'model':animset.name,'path':rel,'controllers':list(range_changes.values()),
                                                              'exact_sfm_out_of_range_behavior_verified':False})
            if unlocked:warn(f'{animset.name}: preserving {len(range_changes)} out-of-range flex controllers for SFM Flex Unlocker; modded SFM equivalence is unverified.')
            else:warn(f'{animset.name}: {len(range_changes)} flex controllers exceed MDL ranges and are clamped; exact SFM out-of-range behavior is unverified.')
        for mesh in meshes:
            keys=mesh.data.shape_keys;curves=AnimationCurves(keys,animset.name+' facial animation')
            target_ranges=json.loads(mesh.get('sfm_flex_target_ranges','{}'))
            if target_ranges:
                counts={}
                for entry in target_ranges.values():counts[entry['source_flex']]=counts.get(entry['source_flex'],0)+1
                REPORT.setdefault('flex_vertex_ranges',[]).append({'model':animset.name,'mesh':mesh.name,
                    'shape_count':len(target_ranges),'intermediate_flexes':{name:count for name,count in counts.items() if count>1},
                    'range_weights_baked':not unlocked,'stereo_shapes':sum(bool(entry.get('stereo_balance_baked')) for entry in target_ranges.values()),
                    'source_renderer_equivalence_verified':False})
                if unlocked and any(count>1 for count in counts.values()):
                    warn(f'{animset.name}: intermediate flex shapes retain raw weights in Flex Unlocker mode; modded range activation is unverified.')
            for key in list(keys.key_blocks)[1:]:
                metadata=target_ranges.get(key.name,{})
                source_name=metadata.get('source_flex',key.name)
                if source_name not in samples[0]:
                    warn(f'{animset.name}: shape key has no MDL flex rule: {key.name}');continue
                vals=[v[source_name] for v in samples]
                if metadata and not unlocked:
                    vals=[target_weight(value,metadata['targets']) for value in vals]
                if metadata.get('partner_index') and not metadata.get('stereo_balance_baked'):
                    message=f'{animset.name}: paired flex {source_name} has no verified stereo vertex balance conversion.'
                    warn(message)
                    if message not in REPORT['unsupported']:REPORT['unsupported'].append(message)
                key.slider_min=min(-1.,min(vals));key.slider_max=max(1.,max(vals))
                key.value=vals[0]
                curves.add(key.path_from_id('value'),frames,vals)
    if meshes and normal_deltas:
        record=REPORT['flex_normal_deltas'][-1]
        try:
            from flex_normals import attach as attach_flex_normals
            record['meshes']=attach_flex_normals(assets,mdl,container,rel)
            record['converted']=True
            record['method']='Native normal fields with evaluated pose/rest matrix drivers'
            record['source_visual_equivalence_verified']=False
        except Exception as exc:
            record['reason']=str(exc)
            message=f'{animset.name}: compiled flex normal changes were not fully imported: {exc}'
            warn(message);REPORT['unsupported'].append(message)
    variants=model_variants(container,mdl,gm,shot,frames,seconds)
    model_visibility(root,members,gm,shot,frames,seconds)
    isolate_model_materials(variants,animset.name)
    material_overrides(variants,gm,shot,frames,seconds,assets)
    from texture_scroll import bake as bake_texture_scroll
    for record in bake_texture_scroll(variants,assets,frames,seconds,Curves):
        record['model']=animset.name;record['shot']=shot.element.name
        REPORT.setdefault('texture_scroll',[]).append(record)
        if not record['converted']:REPORT['unsupported'].append('TextureScroll '+record['material']+': '+record['reason'])
    disable_model_sheen(variants)
    return root


def isolate_model_materials(meshes,model_name):
    """Keep each Source surface independently editable for this model instance."""
    copies={}
    for mesh in meshes:
        for slot in mesh.material_slots:
            original=slot.material
            if original is None:continue
            if original not in copies:
                material=original.copy();material.name=model_name+' / '+original.name
                material['sfm_model_name']=model_name
                material['sfm_material_source_name']=str(original.get('full_path',original.name))
                copies[original]=material
            slot.material=copies[original]


def model_visibility(root,members,gm,shot,frames,seconds):
    """Expose Source visibility on the model root and its rig/attachments.

    Mesh visibility is already combined with skin/bodygroup selection by
    model_variants; do not overwrite those variant-specific switches.
    """
    hidden=[not bool(shot.value(gm,'visible',t,True)) for t in seconds]
    root['sfm_model_initially_visible']=not hidden[0]
    for obj in [root,*members]:
        if obj.type=='MESH':continue
        obj.hide_render=hidden[0];obj.hide_viewport=hidden[0]
        if len(set(hidden))>1:
            curves=Curves(obj,obj.name+' model visibility',reuse=True)
            curves.add('hide_render',frames,hidden,'CONSTANT')
            curves.add('hide_viewport',frames,hidden,'CONSTANT')


def import_camera(shot,element,frames,seconds):
    data=bpy.data.cameras.new(element.name);obj=bpy.data.objects.new(element.name,data)
    bpy.context.scene.collection.objects.link(obj)
    animate_transform(obj,shot,element.get('transform'),frames,seconds,True)
    curves=Curves(data,element.name+' optics')
    lens=[36./(2*math.tan(math.radians(max(.1,min(179.,shot.value(element,'fieldOfView',t,45.))))/2)) for t in seconds]
    # Source widens the stored 4:3 horizontal FOV for the render aspect.
    # A 36 x 27 mm gate with vertical fit preserves that reference angle.
    data.sensor_width=36.;data.sensor_height=27.;data.sensor_fit='VERTICAL';data.lens=lens[0]
    data['sfm_fov_reference_aspect']=4./3.
    curves.add('lens',frames,lens)
    near=[max(.001,float(shot.value(element,'znear',t,1.))*SCALE) for t in seconds]
    far=[max(start+.001,float(shot.value(element,'zfar',t,30000.))*SCALE) for start,t in zip(near,seconds)]
    data.clip_start=near[0];data.clip_end=far[0]
    curves.add('clip_start',frames,near);curves.add('clip_end',frames,far)
    data.dof.use_dof=element.get('depthOfFieldQuality',0)>0
    focus=[max(.001,shot.value(element,'focalDistance',t,100.)*SCALE) for t in seconds]
    curves.add('dof.focus_distance',frames,focus)
    preserved={}
    for source_key,target_key in (('toneMapScale','sfm_tone_map_scale'),('bloomScale','sfm_bloom_scale'),
                                  ('aperture','sfm_aperture_inches'),('shutterSpeed','sfm_shutter_speed_seconds')):
        values=[shot.value(element,source_key,t,None) for t in seconds]
        if any(value is None for value in values):continue
        values=[float(value) for value in values]
        data[target_key]=values[0]
        curves.add('['+json.dumps(target_key)+']',frames,values)
        preserved[source_key]={'native_property':target_key,'minimum':min(values),'maximum':max(values),'applied_to_render':False}
    data['sfm_camera_name']=element.name
    if preserved:REPORT.setdefault('camera_effect_settings',[]).append({'camera':element.name,'shot':shot.element.name,'preserved':preserved})
    warn('SFM aperture, motion blur, bloom, AO and tonemapping do not reproduce exactly in Blender.')
    return obj


def import_volumetric(shot,element,light,frames,seconds):
    enabled=[bool(shot.value(element,'volumetric',t,False)) for t in seconds]
    if not any(enabled):return
    from volume_quality import configure_beam_sampling
    configure_beam_sampling(bpy.context.scene)
    # A closed unit cone points down Blender's spotlight axis. Native animation
    # keeps the beam editable and usable without addons or scripted drivers.
    segments=64
    vertices=[(0,0,0)]+[(math.cos(i*math.tau/segments),math.sin(i*math.tau/segments),-1) for i in range(segments)]
    faces=[(0,1+i,1+(i+1)%segments) for i in range(segments)]
    faces.append(tuple(range(segments,0,-1)))
    mesh=bpy.data.meshes.new(element.name+' beam');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(element.name+' volumetric beam',mesh)
    obj.display_type='WIRE'
    bpy.context.scene.collection.objects.link(obj);obj.parent=light
    material=bpy.data.materials.new(element.name+' scattering');material.use_nodes=True
    nodes=material.node_tree.nodes;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');scatter=nodes.new('ShaderNodeVolumeScatter')
    scatter.inputs['Color'].default_value=(1,1,1,1);scatter.inputs['Anisotropy'].default_value=.35
    material.node_tree.links.new(scatter.outputs['Volume'],output.inputs['Volume'])
    mesh.materials.append(material)
    scales=[];densities=[]
    for t,on in zip(seconds,enabled):
        distance=max(.01,float(shot.value(element,'maxDistance',t,600.))*SCALE)
        horizontal=math.radians(max(1.,min(179.,float(shot.value(element,'horizontalFOV',t,45.)))))
        vertical=math.radians(max(1.,min(179.,float(shot.value(element,'verticalFOV',t,45.)))))
        scales.append((math.tan(horizontal/2)*distance,math.tan(vertical/2)*distance,distance))
        # Normalize optical depth against beam length; Source intensity is not
        # a physical scattering coefficient and therefore needs approximation.
        densities.append(.15*max(0.,float(shot.value(element,'volumetricIntensity',t,1.)))/distance if on else 0.)
    obj.scale=scales[0];scatter.inputs['Density'].default_value=densities[0]
    Curves(obj,element.name+' beam shape').add('scale',frames,scales)
    Curves(material.node_tree,element.name+' beam intensity').add(scatter.inputs['Density'].path_from_id('default_value'),frames,densities)
    obj['sfm_volumetric']=True
    REPORT['assets'].append({'type':'volumetric_light','name':element.name,'method':'bounded Volume Scatter cone','animated':True})
    warn('SFM volumetric lights use bounded physical scattering cones; Source noise, plane slicing and beam brightness are approximated.')


def import_light(shot,element,frames,seconds,assets=None):
    data=bpy.data.lights.new(element.name,'SPOT');obj=bpy.data.objects.new(element.name,data)
    bpy.context.scene.collection.objects.link(obj)
    animate_transform(obj,shot,element.get('transform'),frames,seconds,True)
    curves=Curves(data,element.name+' light properties')
    colors=[];energy=[];cones=[];radius=[]
    for t in seconds:
        color=shot.value(element,'color',t,(255,255,255,255))
        # Source light color is stored as 0-255 sRGB.
        rgb=[max(0.,float(c)/255.) for c in color[:3]]
        colors.append([c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb])
        gain=float(JOB.get('light_gain',10.))
        energy.append(float(shot.value(element,'intensity',t,100.))*gain)
        cones.append(math.radians(max(1.,min(179.,float(shot.value(element,'horizontalFOV',t,45.))))))
        radius.append(max(0.,float(shot.value(element,'radius',t,0.))*SCALE))
    curves.add('color',frames,colors);curves.add('energy',frames,energy);curves.add('spot_size',frames,cones);curves.add('shadow_soft_size',frames,radius)
    data.color=colors[0];data.energy=energy[0];data.spot_size=cones[0]
    shadows=[bool(shot.value(element,'castsShadows',t,True)) for t in seconds]
    curves.add('use_shadow',frames,shadows,interpolation='CONSTANT')
    data.use_shadow=shadows[0]
    data['sfm_light_gain']=float(JOB.get('light_gain',10.))
    if assets is not None:
        try:
            from projected_light import import_cookie
            path=import_cookie(assets,shot,element,data,frames,seconds,Curves)
            if path:REPORT['assets'].append({'type':'projected_light_texture','name':element.name,'path':path,'converted':True,'method':'Cycles perspective cookie'})
        except Exception as exc:
            warn(f'{element.name}: projected texture conversion failed: {exc}')
            REPORT['unsupported'].append(f'{element.name}: projected texture: {exc}')
    try:
        from light_attenuation import apply as apply_attenuation
        REPORT.setdefault('light_attenuation',[]).append(apply_attenuation(data,shot,element,frames,seconds,Curves,SCALE))
    except Exception as exc:
        message=f'{element.name}: attenuation conversion failed: {exc}'
        warn(message);REPORT['unsupported'].append(message)
    import_volumetric(shot,element,obj,frames,seconds)
    warn('Projected lights use approximate Cycles texture projection; Source attenuation and filtering require review.')
    return obj


def import_hierarchy(shot,objects,frames,seconds,model_loader=None,particle_loader=None,assets=None):
    """Keep Source local DAG transforms, including bone attachment parents."""
    seen=set()
    def walk(dag,parent=None,parent_axis=False):
        if dag is None:return
        identity=eid(dag)
        if identity in seen:
            warn(f'{dag.name}: scene DAG has a repeated or cyclic parent; using its first placement.')
            return
        seen.add(identity)
        obj=objects.get(identity)
        axis=kind(dag,'DmeCamera') or kind(dag,'DmeProjectedLight')
        if obj is None:
            if kind(dag,'DmeProjectedLight'):obj=import_light(shot,dag,frames,seconds,assets)
            elif kind(dag,'DmeCamera'):obj=import_camera(shot,dag,frames,seconds)
            elif kind(dag,'DmeGameModel') and model_loader:
                try:obj=model_loader(dag)
                except Exception as exc:
                    REPORT['errors'].append(f'Hierarchy model {dag.name}: {exc}')
                    obj=None
            if obj is None:
                obj=bpy.data.objects.new(dag.name+' DAG',None)
                bpy.context.scene.collection.objects.link(obj)
                if kind(dag,'DmeGameModel'):
                    obj['sfm_missing_model']=str(dag.get('modelName',''))
                animate_transform(obj,shot,dag.get('transform'),frames,seconds)
            objects[identity]=obj
        obj.parent=parent
        obj['sfm_dag_id']=identity
        if dag.get('transform') is not None:obj['sfm_transform_id']=eid(dag['transform'])
        if is_particle_system(dag):
            REPORT['unsupported'].append(f'Particle simulation/rendering: {dag.name}')
            if particle_loader:particle_loader(dag,obj)
        # Camera/light local axes were changed for Blender. Undo that basis
        # change for Source-space children while preserving the parent's motion.
        obj.matrix_parent_inverse=AXIS.inverted() if parent_axis else Matrix.Identity(4)
        for child in dag.get('children',[]):walk(child,obj,axis)
    walk(shot.element.get('scene'))
    REPORT['assets'].append({'type':'scene_hierarchy','nodes':len(seen)})


def configure_scene(scene,session):
    scene.view_settings.view_transform='Standard'
    scene.view_settings.look='None'
    scene.render.engine='CYCLES'
    scene.cycles.samples=64
    scene.render.resolution_x=session.width;scene.render.resolution_y=session.height;scene.render.resolution_percentage=100
    fps=round(session.fps);scene.render.fps=fps;scene.render.fps_base=fps/session.fps
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.world=bpy.data.worlds.new(scene.name+' world');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.02,.02,.02,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.1


def import_map(assets,shot):
    if not shot.map:return
    from SourceIO.blender_bindings.source1.bsp.import_bsp import import_bsp
    from SourceIO.blender_bindings.operators.import_settings_base import Source1BSPSettings
    rel=safe_relative(shot.map)
    if not rel.startswith('maps/'):rel='maps/'+rel
    if not rel.lower().endswith('.bsp'):rel+='.bsp'
    event('map',f'Importing {rel}')
    buf=assets.buffer(rel)
    if buf is None:raise FileNotFoundError(f'Map missing: {rel}')
    class Settings:
        scale=SCALE;light_scale=1.;load_props=True;load_lights=True;load_decals=True
        load_static_props=True;load_triggers=False;load_info=False;load_logic=False;load_ropes=True
        import_textures=True;import_cubemaps=True;use_bvlg=False
    previous_objects=set(bpy.context.scene.objects)
    imported_bsp=import_bsp(assets.TinyPath(rel),buf,assets.cm,Settings())
    map_objects=set(bpy.context.scene.objects)-previous_objects
    # Resolve surfaces before copying atlas-specific materials, and before sky
    # fog wraps their outputs. Late shader generation would erase the binding.
    resolve_pending_materials(assets)
    from bsp_lightmaps import apply as apply_bsp_lightmaps
    lightmap_record=apply_bsp_lightmaps(imported_bsp,map_objects,SCALE)
    REPORT['assets'].append({'type':'map_lightmaps','map':rel,**lightmap_record})
    if lightmap_record['bump_faces_using_base_block'] or lightmap_record['additional_styles'] or lightmap_record['unsupported_materials']:
        REPORT['unsupported'].append(f'Map lightmap directional blocks, animated styles or grouped shaders need review: {rel}')
    from map_props import load as load_map_props
    prop_records=load_map_props(assets,map_objects,warn)
    resolve_pending_materials(assets)
    from prop_lighting import apply as apply_prop_lighting
    prop_lighting_record=apply_prop_lighting(imported_bsp,map_objects,lightmap_record['mode']!='LDR')
    REPORT['assets'].append({'type':'map_prop_lighting','map':rel,**prop_lighting_record})
    if prop_lighting_record['rejected'] or prop_lighting_record['unsupported_materials'] or prop_lighting_record['missing_props']:
        REPORT['unsupported'].append(f'Map prop baked lighting has missing, mismatched or unsupported assets: {rel}')
    prop_meshes={child for obj in map_objects if obj.instance_collection for child in obj.instance_collection.all_objects if child.type=='MESH'}
    prop_meshes.update(child for obj in map_objects for child in obj.children_recursive if child.type=='MESH')
    disable_model_sheen(prop_meshes)
    for record in prop_records:
        REPORT['assets'].append({'type':'map_prop','map':rel,**record})
        if not record['converted']:REPORT['unsupported'].append(f'Missing map prop: {record["path"]}')
        if record.get('tint_converted') is False:REPORT['unsupported'].append(f'Map prop tint {record["path"]}: '+', '.join(record['tint_unsupported']))
    entities=imported_bsp.get_lump('LUMP_ENTITIES')
    sky_cameras=[entity for entity in entities.entities if entity.get('classname')=='sky_camera'] if entities else []
    for camera in sky_cameras:
        record={'type':'3d_skybox','map':rel,'camera':dict(camera),'converted':False}
        try:
            from sky_spatial import classify,point_area,leaf_areas
            record['spatial']=classify(imported_bsp,camera)
            from sky_geometry import split_faces,apply_camera_transform
            record['transformed_brush_objects']=[]
            record['transformed_prop_objects']=[]
            for obj in map_objects:
                if obj.instance_collection and obj.get('entity_data',{}).get('type')=='static_props':
                    point=tuple(float(v)/SCALE for v in obj.location)
                    areas=leaf_areas(imported_bsp,obj.get('sfm_bsp_prop_leaves',[]))
                    if not areas:
                        origin_area=point_area(imported_bsp,point)
                        if origin_area is not None:areas={origin_area}
                    if areas=={record['spatial']['area']}:
                        apply_camera_transform(obj,camera,SCALE)
                        record['transformed_prop_objects'].append(obj.name)
                    elif record['spatial']['area'] in areas:
                        warn(f'{rel}: prop spans both sky and playable areas: {obj.name}; placement retained for review.')
                if obj.type!='MESH':continue
                sky=split_faces(obj,record['spatial']['sky_faces'])
                if sky is not None:
                    apply_camera_transform(sky,camera,SCALE)
                    record['transformed_brush_objects'].append(sky.name)
            from sky_fog import apply as apply_sky_fog
            sky_objects=[bpy.data.objects[name] for name in record['transformed_brush_objects']+record['transformed_prop_objects']]
            record['fog_materials']=apply_sky_fog(sky_objects,camera,SCALE,bpy.context.scene)
        except Exception as exc:
            record['classification_error']=str(exc)
            warn(f'{rel}: cannot classify 3D skybox geometry: {exc}')
        REPORT['assets'].append(record)
        issue=f'3D skybox geometry transform and fog: {rel}'
        if issue not in REPORT['unsupported']:REPORT['unsupported'].append(issue)
        warn(f'{rel}: 3D skybox position/scale and surface fog are converted; fog shader matching, visibility/depth ordering and branch-specific rotation remain approximate.')
    REPORT['assets'].append({'type':'map','path':rel})
    world=bpy.context.scene.world
    sky_images=[node.image for node in world.node_tree.nodes if node.type=='TEX_ENVIRONMENT' and node.image] if world and world.use_nodes else []
    if sky_images:
        for image in sky_images:
            if not image.packed_file:image.pack()
        world['sfm_map_skybox']=world.name
        REPORT['assets'].append({'type':'skybox','map':rel,'name':world.name,'dynamic_range':world.get('sfm_sky_dynamic_range','SDR'),'images':[image.name for image in sky_images],'packed':all(bool(image.packed_file) for image in sky_images)})
    else:warn(f'Map skybox was not resolved: {rel}')


def place_sounds(assets,clips,scene,fps,origin=0.,shot=None,gain=1.):
    editor=scene.sequence_editor_create()
    collection=editor.strips if hasattr(editor,'strips') else editor.sequences
    channel=max([31]+[strip.channel for strip in collection])+1
    audio_curves=None
    for clip,clock in clips:
        sound=clip.get('sound')
        if sound is None:continue
        rel=str(sound.get('gameSoundName') or sound.get('soundname') or clip.name)
        try:
            if hasattr(assets,'sound_scripts'):
                from sound_scripts import SoundScripts,relative_sound
                direct=str(sound.get('soundname',''))
                if Path(direct).suffix.lower() in ('.wav','.mp3','.ogg','.flac'):
                    rel,script=relative_sound(direct),None
                else:
                    mapname=shot.map if shot else ''
                    if mapname not in assets.sound_scripts:
                        assets.sound_scripts[mapname]=SoundScripts(assets,[mapname] if mapname else [])
                        for issue in assets.sound_scripts[mapname].issues:warn(issue)
                    rel,script=assets.sound_scripts[mapname].resolve(sound)
                if script:
                    REPORT['assets'].append({'type':'sound_script',**script})
                    if script['random_choice_approximation']:warn(f'{script["name"]}: random sound variant is not recorded in DMX; selected {rel}.')
            else:
                from sound_scripts import relative_sound
                rel=relative_sound(sound.get('soundname',''))
            path=assets.materialize(rel)
            tf=clip.get('timeFrame') or {}
            start=clock.global_time(float(tf.get('offset',0.)))-origin
            duration=float(tf.get('duration',0.))*abs(clock.rate*float(tf.get('scale',1.)))
            if duration<=0:continue
            frame_start=round(start*fps)+1
            frame_end=round((start+duration)*fps)+1
            frames=list(range(frame_start,frame_end+1))
            pitches=[float(shot.value(sound,'pitch',origin+(frame-1)/fps,sound.get('pitch',100.))) if shot else float(sound.get('pitch',100.)) for frame in frames]
            if len(pitches)<2:pitches*=2
            baked=abs(clock.rate-1)>1e-6 or any(abs(p-100)>1e-6 for p in pitches)
            offset=max(0,round(float(tf.get('offset',0.))*fps))
            if baked:
                from audio_bake import bake
                key=hashlib.sha256(json.dumps([rel,float(tf.get('offset',0.)),duration,clock.rate,pitches]).encode()).hexdigest()[:20]
                path=bake(path,Path(JOB['output']).with_suffix('.assets')/'sound/baked'/f'{key}.wav',float(tf.get('offset',0.)),duration,clock.rate,pitches,fps)
                offset=0
            # The underlying media begins earlier; trim it to the authored clip.
            strip=collection.new_sound(clip.name,str(path),channel,round(start*fps)+1-offset)
            strip.frame_offset_start=offset
            desired_end=frame_end
            if desired_end<strip.frame_final_end:strip.frame_final_end=desired_end
            strip.volume=float(sound.get('volume',1.));strip.mute=clip.get('mute',False)
            parent_rate=abs(clock.rate*float(tf.get('scale',1.)))
            fade_in=max(0.,float(clip.get('fadeIn',0.)))*parent_rate
            fade_out=max(0.,float(clip.get('fadeOut',0.)))*parent_rate
            values=[]
            for frame in frames:
                elapsed=max(0.,min(duration,(frame-frame_start)/fps))
                volume=shot.value(sound,'volume',origin+(frame-1)/fps,sound.get('volume',1.)) if shot else sound.get('volume',1.)
                values.append(envelope(elapsed,duration,fade_in,fade_out,volume*gain))
            strip.volume=values[0] if values else float(sound.get('volume',1.))*gain
            if values and (fade_in or fade_out or len(set(values))>1):
                if audio_curves is None:audio_curves=Curves(scene,scene.name+' sound envelopes',reuse=True)
                audio_curves.add(strip.path_from_id('volume'),frames,values)
            strip.sound.pack()
            strip.sound.filepath='//'+path.relative_to(Path(JOB['output']).parent).as_posix()
            REPORT['assets'].append({'type':'sound','path':rel,'packed':bool(strip.sound.packed_file),'start_frame':strip.frame_final_start,'end_frame':strip.frame_final_end,'media_offset':offset,'fade_in_seconds':fade_in,'fade_out_seconds':fade_out,'volume_animated':bool(fade_in or fade_out or len(set(values))>1)})
            REPORT['assets'][-1].update({'audio_baked':baked,'source_offset_seconds':float(tf.get('offset',0.)),'source_clock_rate':clock.rate,'pitch_range':[min(pitches),max(pitches)]})
            channel+=1
        except Exception as exc:REPORT['errors'].append(f'Sound {rel}: {exc}')


def convert(job):
    REPORT['lighting']={'brightness_multiplier':float(job.get('light_gain',10.)),'particle_glow_multiplier':float(job.get('particle_light_gain',1.)),'view_transform':'Standard','approximate':True}
    event('inspect','Reading full SFM session',0)
    session=Session(job['session']);REPORT['session']=session.summary()
    Curves.configure_animation_sampling(session.fps,job.get('animation_keyframe_fps',0))
    particle_file_hints={eid(e.get('particle system')):e.get('particleFiles',[]) for e in session.data.elements if e.type.lstrip('C')=='DmeAnimationSet' and e.get('particle system') is not None}
    if bpy.app.version<(5,0,0):raise ValueError('This converter currently requires Blender 5.0 or newer.')
    event('assets','Mounting SFM asset paths',.05)
    import SourceIO
    from SourceIO.blender_bindings.bindings import register
    register()
    assets=Assets(job)
    assets.sound_scripts={}
    # SourceIO's default sequence cache can live beside a game installation.
    # Keep generated media beside this output instead, so the SFM tree is read-only.
    from SourceIO.blender_bindings.utils import texture_utils
    from SourceIO.blender_bindings.source1 import vtf
    cache_roots=lambda *args,**kwargs:[assets.TinyPath(str(assets.sidecar/'textures'))]
    texture_utils.get_asset_cache_roots=cache_roots
    vtf.get_asset_cache_roots=cache_roots
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    master=bpy.context.scene;master.name='SFM Master Timeline'
    configure_scene(master,session)
    editor=master.sequence_editor_create()
    strips=editor.strips if hasattr(editor,'strips') else editor.sequences
    for index,shot in enumerate(session.shots):
        event('shot',f'Converting {shot.element.name} ({index+1}/{len(session.shots)})',.1+.75*index/len(session.shots))
        scene=bpy.data.scenes.new(shot.element.name);bpy.context.window.scene=scene
        configure_scene(scene,session)
        following=session.shots[index+1] if index+1<len(session.shots) else None
        count=shot_frame_count(shot,session.fps,following)
        from preview_range import frame_range
        first_frame,count=frame_range(count,job)
        if job.get('preview_frames') is not None:
            REPORT['diagnostic_preview']={
                'complete_animation_verified':False,
                'historical_control_motion_verified':False,
                'limitation':'Scene animation keys cover the requested preview range; particle birth-history queries outside that range may use clamped transforms'}
        frames=np.arange(first_frame,first_frame+count);seconds=shot.start+(frames-1)/session.fps
        scene.frame_start=first_frame;scene.frame_end=first_frame+count-1
        REPORT['shots'].append({'name':shot.element.name,'frames':count,'start':shot.start,'frame_start':first_frame,'frame_end':scene.frame_end})
        for issue in shot.issues:warn(issue)
        try:import_map(assets,shot)
        except Exception as exc:REPORT['errors'].append(str(exc));traceback.print_exc()
        imported={}
        for animset in shot.element.get('animationSets',[]):
            gm=animset.get('gameModel')
            if gm is not None:
                try:imported[eid(gm)]=import_model(assets,shot,animset,frames,seconds)
                except Exception as exc:REPORT['errors'].append(f'Model {animset.name}: {exc}');traceback.print_exc()
        camera=shot.element.get('camera')
        if camera is not None:
            scene.camera=import_camera(shot,camera,frames,seconds)
            imported[eid(camera)]=scene.camera
            from camera_blur import apply as apply_camera_blur
            blur=apply_camera_blur(scene,shot,camera,frames,seconds,session.fps,Curves)
            REPORT.setdefault('camera_motion_blur',[]).append(blur)
            for effect in REPORT.get('camera_effect_settings',[]):
                if effect['camera']==camera.name and effect['shot']==shot.element.name and 'shutterSpeed' in effect['preserved']:
                    effect['preserved']['shutterSpeed'].update(native_render_property='render.motion_blur_shutter',applied_to_render=bool(blur['enabled_frames']))
            if blur['enabled_frames']:warn('Camera shutter duration is mapped to native motion blur; Source sampling and shutter phase remain approximate.')
        else:REPORT['errors'].append(f'{shot.element.name}: no active shot camera')
        def load_unlisted(dag):
            class AnimationSet(dict):name=dag.name
            return import_model(assets,shot,AnimationSet(gameModel=dag),frames,seconds)
        pending_particles=[]
        if job.get('experimental_refraction'):assets.particle_materials={}
        def load_particle(dag,obj):
            from particles import Definitions
            if not hasattr(assets,'particles'):assets.particles=Definitions(assets)
            try:
                descriptor=assets.particles.describe(dag,particle_file_hints.get(eid(dag),[]))
                from particles import timing_controller
                descriptor['animation']=timing_controller(dag,obj,shot,frames,seconds,Curves)
                from particle_resource_packing import encode as encode_resource
                if not hasattr(assets,'particle_resource_texts'):assets.particle_resource_texts={}
                descriptor['resources']=[]
                for path,data in assets.particles.resources(descriptor['dependencies']):
                    record={'path':path,'embedded':data is not None}
                    if data is None:warn(f'Particle {dag.name}: missing resource {path}')
                    else:
                        if path not in assets.particle_resource_texts:
                            event('particles',f'{dag.name}: embedding {path} ({len(data)/1048576:.1f} MB)')
                            packed=bpy.data.texts.new(path+' packed Source resource')
                            packed.from_string(encode_resource(data))
                            assets.particle_resource_texts[path]=packed.name
                        record['text']=assets.particle_resource_texts[path];record['bytes']=len(data)
                    descriptor['resources'].append(record)
                from particles import sprite_material,material_failure
                if not hasattr(assets,'particle_materials'):assets.particle_materials={}
                descriptor['materials']=[]
                for path in descriptor['dependencies']:
                    if not path.lower().endswith('.vmt'):continue
                    try:
                        if path not in assets.particle_materials:assets.particle_materials[path]=sprite_material(assets,path,experimental_refraction=bool(job.get('experimental_refraction')),scene=scene,time_offset=shot.start)
                        material=assets.particle_materials[path]
                        descriptor['materials'].append({'path':path,'blender_material':material.name,'approximate':True})
                        warn(material['sfm_particle_approximation'])
                    except Exception as exc:
                        descriptor['materials'].append(material_failure(path,exc))
                        warn(f'Particle material {path}: {exc}')
                REPORT.setdefault('particles',[]).append(descriptor)
                text=bpy.data.texts.new(dag.name+' Source particle definition');text.write(json.dumps(descriptor,indent=2))
                obj['sfm_particle_definition_text']=text.name
                pending_particles.append((dag,descriptor,text))
                if descriptor['pcf']:
                    import base64
                    if not hasattr(assets,'particle_pcf_texts'):assets.particle_pcf_texts={}
                    if descriptor['pcf'] not in assets.particle_pcf_texts:
                        buf=assets.buffer(descriptor['pcf']);buf.seek(0)
                        raw=bpy.data.texts.new(Path(descriptor['pcf']).name+' packed Source PCF');raw.from_string(encode_resource(buf.read()))
                        assets.particle_pcf_texts[descriptor['pcf']]=raw.name
                    obj['sfm_packed_pcf_text']=assets.particle_pcf_texts[descriptor['pcf']]
                    REPORT['assets'].append({'type':'particle_definition','path':descriptor['pcf'],'effect':descriptor['effect'],'embedded':True})
            except Exception as exc:REPORT['errors'].append(f'Particle {dag.name}: {exc}')
        try:import_hierarchy(shot,imported,frames,seconds,load_unlisted,load_particle,assets)
        except Exception as exc:REPORT['errors'].append(f'Scene hierarchy {shot.element.name}: {exc}');traceback.print_exc()
        from constraints import bake as bake_constraints
        try:
            records=bake_constraints(shot,imported,frames,seconds,transform,AXIS,Curves,
                                     progress=lambda message:event('animation',message))
            for record in records:
                record['shot']=shot.element.name
                REPORT.setdefault('constraints',[]).append(record)
                if not record['converted']:REPORT['unsupported'].append(f'{record["type"]}: {record["name"]} ({record.get("reason","not evaluated")})')
                elif record['type']=='DmeRigIKConstraintOperator':warn('Two-bone IK is geometrically baked using SFM joint offsets; reach clamping and pole/roll behavior may differ from Source.')
        except Exception as exc:
            REPORT['errors'].append(f'Constraint evaluation {shot.element.name}: {exc}');traceback.print_exc()
        if pending_particles:
            try:
                from particle_control_objects import import_missing as import_missing_particle_controls
                particle_controls=import_missing_particle_controls(pending_particles,scene,shot,frames,seconds,animate_transform)
                if particle_controls['created']:
                    REPORT.setdefault('particle_control_points',[]).append({'shot':shot.element.name,**particle_controls})
                    event('particles',f'Imported {particle_controls["created"]} standalone particle control-point transform(s)')
            except Exception as exc:
                REPORT['errors'].append(f'Particle control-point transforms {shot.element.name}: {exc}')
                traceback.print_exc()
        from particle_bake import bake as bake_particles
        from particle_model_scene import factory as model_particle_factory
        model_factory=model_particle_factory(session,imported,assets,scene,shot,session.fps,SCALE)
        from particle_collision_scene import prepare as prepare_particle_collision,required as collision_required
        collision_trace=None;collision_report=None
        if collision_required([descriptor for _,descriptor,_ in pending_particles]):
            try:
                collision_trace,collision_report=prepare_particle_collision(session,shot,assets)
                collision_report={**collision_report,'production_enabled':True,'approximate':True,'shot':shot.element.name}
                warn('Particle collision: approximate BSP brush kill traces, including supported static brush entities; Source cached-plane behavior, VPhysics shapes and boundary epsilon differ.')
            except Exception as exc:
                collision_report={'shot':shot.element.name,'production_enabled':False,'reason':str(exc)}
                warn('Particle trace collision unavailable: '+str(exc))
            REPORT.setdefault('particle_collision',[]).append(collision_report)
        for dag,descriptor,text in pending_particles:
            bake_started=time.perf_counter()
            try:
                tint_provider=None;tint_report=None
                if job.get('experimental_tint'):
                    from particle_tint_scene import required as tint_required,prepare as prepare_tint
                    if tint_required(descriptor):
                        try:
                            tint_provider,tint_report=prepare_tint(shot,descriptor,scene,assets,session.fps,scale=SCALE,settings=job.get('particle_tint_settings'))
                            warn('Particle tint: approximate static map lighting sampled at birth; Source step timing, dynamic styles and prop/displacement occlusion remain unverified.')
                        except Exception as exc:
                            tint_report={'map':shot.map,'available':False,'reason':str(exc)}
                            warn('Particle tint unavailable: '+str(exc))
                if collision_report is not None and collision_required([descriptor]):descriptor['collision_scene']=collision_report
                descriptor['bake']=bake_particles(dag,descriptor,shot,scene,frames,seconds,session.fps,assets.particle_materials,Curves,SCALE,progress=lambda message:event('particles',message),experimental_decay=bool(job.get('experimental_delayed_decay',False)),experimental_pull=bool(job.get('experimental_pull',False)),experimental_spline=bool(job.get('experimental_spline',False)),experimental_partial_lock=bool(job.get('experimental_partial_lock',False)),collision_trace=collision_trace,tint_provider=tint_provider,model_factory=model_factory,simulation_contexts={} if job.get('experimental_parent',False) else None,retain_leaf_contexts=False,development_pull_lock=bool(job.get('experimental_pull_lock',False)),development_noise=bool(job.get('experimental_noise',False)),particle_frame_step=int(job.get('particle_frame_step',1)))
                if tint_report is not None:
                    descriptor['tint_lighting']={**tint_report,'available':tint_provider is not None,
                        'lighting_queries':len(tint_provider.query_records) if tint_provider else 0,
                        'parent_cache_reads':len(tint_provider.parent_reads) if tint_provider else 0}
                from particle_validation import converted as particle_converted
                descriptor['converted']=bool(descriptor['bake']) and all(particle_converted(r) for r in descriptor['bake'])
                descriptor['rendered']=bool(descriptor['bake']) and all(r['rendered'] for r in descriptor['bake'])
                descriptor['bake_elapsed_seconds']=time.perf_counter()-bake_started
                event('particles',f'{dag.name}: particle bake finished in {descriptor["bake_elapsed_seconds"]:.1f} seconds')
                text.clear();text.write(json.dumps(descriptor,indent=2))
                if any(r['rendered'] for r in descriptor['bake']):warn('Particles: supported sprites use native frame meshes or maintained-count geometry nodes; Source RNG/tick phase, velocity noise, drag, fade easing, texture sheets and motion blur are approximate.')
                if descriptor['converted']:
                    label=f'Particle simulation/rendering: {dag.name}'
                    if label in REPORT['unsupported']:REPORT['unsupported'].remove(label)
                for record in descriptor['bake']:
                    if not particle_converted(record):REPORT['unsupported'].append(f'Particle effect {record["effect"]}: {record.get("reason","not converted")}')
            except Exception as exc:REPORT['errors'].append(f'Particle bake {dag.name}: {exc}')
        if job.get('experimental_refraction'):
            refraction_objects=[obj for obj in scene.objects if obj.get('sfm_baked_frame') is not None and len(obj.data.materials)==1 and obj.data.materials[0].get('sfm_refraction_experimental')]
            if refraction_objects:
                try:
                    from particle_refraction_scene import install as install_refraction
                    install_refraction(scene,refraction_objects)
                    REPORT.setdefault('experimental_refraction',[]).append({'shot':shot.element.name,'meshes':len(refraction_objects),'installed':True,'source_parity':False})
                    warn('Experimental particle refraction enabled: depth ordering, shot phase and Source visual matching remain approximate.')
                except Exception as exc:
                    REPORT['errors'].append(f'Experimental refraction {shot.element.name}: {exc}')
                    paths=[m.get('sfm_particle_material','') for obj in refraction_objects for m in obj.data.materials if m and m.get('sfm_refraction_experimental')]
                    from particle_refraction_status import failed as failed_refraction
                    for dag,descriptor,text in pending_particles:
                        if failed_refraction(descriptor,paths,exc):
                            text.clear();text.write(json.dumps(descriptor,indent=2))
                    REPORT.setdefault('experimental_refraction',[]).append({'shot':shot.element.name,'installed':False,'reason':str(exc)})
                    failed_collection=bpy.data.collections.new(shot.element.name+' failed refraction geometry')
                    scene.collection.children.link(failed_collection);failed_collection.hide_render=True
                    for obj in refraction_objects:
                        failed_collection.objects.link(obj)
                        for collection in list(obj.users_collection):
                            if collection!=failed_collection:collection.objects.unlink(obj)
                        if obj.animation_data:
                            for driver in obj.animation_data.drivers:
                                if driver.data_path=='hide_render':driver.mute=True
                        obj.hide_render=True
        from sky_fog import animate as animate_sky_fog
        animate_sky_fog(scene,frames,Curves)
        place_sounds(assets,shot.sounds,scene,session.fps,shot.start,shot,
                     float(session.master.get('volume',1.))*float(shot.element.get('volume',1.)))
        place_sounds(assets,session.sounds,scene,session.fps,shot.start,
                     gain=float(session.master.get('volume',1.)))
        scene.sync_mode='AUDIO_SYNC'
        scene.frame_set(1)
        strip=strips.new_scene(shot.element.name,scene,1,round(shot.start*session.fps)+1)
        strip.frame_final_duration=count
        if hasattr(strip,'scene_input'):strip.scene_input='CAMERA'
        if hasattr(strip,'use_sequence'):strip.use_sequence=False
        strip.volume=0. # Master audio is explicitly mixed below, avoiding duplication.
        marker=master.timeline_markers.new(shot.element.name,frame=round(shot.start*session.fps)+1)
    bpy.context.window.scene=master
    master.frame_start=1;master.frame_end=max(1,max(s.frame_final_end for s in strips)-1)
    place_sounds(assets,session.sounds,master,session.fps,gain=float(session.master.get('volume',1.)))
    for shot in session.shots:
        place_sounds(assets,shot.sounds,master,session.fps,0.,shot,
                     float(session.master.get('volume',1.))*float(shot.element.get('volume',1.)))
    master.sync_mode='AUDIO_SYNC'
    from master_camera import create_cameras
    REPORT['master_cameras']=create_cameras(master,Curves,
        progress=lambda message:event('animation',message))
    event('pack','Packing textures and auditing references',.9)
    resolve_pending_materials(assets)
    REPORT['zero_sheen_principled_shaders']=disable_material_sheen(bpy.data.materials)
    from tile_emission import apply as apply_tile_emission
    REPORT['animated_tile_emission_shaders']=apply_tile_emission(bpy.data.materials)
    from packed_sequences import pack_sequences
    if hasattr(assets,'particles'):REPORT['particle_definition_lookup']=assets.particles.lookup_summary()
    REPORT['packed_sequences']=pack_sequences(use_source_rate=True)
    if any(r.get('source_frame_rate',0)>0 for r in REPORT['packed_sequences']):
        warn('Animated textures use authored Source playback rates; exact SFM proxy phase and per-entity timing are unverified.')
    packed=0
    for image in bpy.data.images:
        packed_extension='.exr' if image.file_format=='OPEN_EXR' else '.png'
        if image.source=='FILE':
            if image.packed_file is not None:
                packed+=1
                # Relabel packed data without asking Blender to reload the
                # template author's obsolete external image path.
                image.filepath_raw='//textures/'+re.sub(r'[^a-zA-Z0-9_.-]','_',image.name)+packed_extension
            elif image.users:
                try:
                    image.pack();packed+=1
                    image.filepath_raw='//textures/'+re.sub(r'[^a-zA-Z0-9_.-]','_',image.name)+packed_extension
                except Exception as exc:REPORT['errors'].append(f'Texture {image.name}: cannot pack ({exc})')
        elif image.source in ('SEQUENCE','MOVIE') and image.users:
            source=Path(bpy.path.abspath(image.filepath))
            if not source.is_file():
                REPORT['errors'].append(f'External media missing: {image.name}');continue
            destination=assets.sidecar/'textures'/hashlib.sha256(str(source).encode()).hexdigest()[:12]
            destination.mkdir(parents=True,exist_ok=True)
            if image.source=='SEQUENCE':
                prefix=re.sub(r'\d+$','',source.stem)
                files=[p for p in source.parent.glob(prefix+'*'+source.suffix) if p.is_file()]
            else:files=[source]
            for media in files:
                target=destination/media.name
                if media.resolve()!=target.resolve():shutil.copy2(media,target)
            image.filepath='//'+(destination/source.name).relative_to(Path(job['output']).parent).as_posix()
            REPORT['assets'].append({'type':'animated_texture','name':image.name,'media_files':len(files),'relative_path':image.filepath})
            warn('Animated textures require moving the .assets folder with the .blend.')
    REPORT['packed_images']=packed
    REPORT['packed_sounds']=sum(bool(sound.packed_file) for sound in bpy.data.sounds)
    REPORT.setdefault('constraints',[])
    for e in session.data.elements:
        if is_particle_system(e) and not any(p.get('system')==e.name for p in REPORT.get('particles',[])):
            REPORT['unsupported'].append(f'{e.type}: {e.name}')
    REPORT['unsupported']=sorted(set(REPORT['unsupported']))
    REPORT['blender_version']=bpy.app.version_string
    REPORT['counts']={'objects':len(bpy.data.objects),'materials':len(bpy.data.materials),'images':len(bpy.data.images),'actions':len(bpy.data.actions)}
    REPORT['animation_key_sampling']=Curves.animation_sampling_report()
    REPORT['status']='partial' if REPORT['errors'] or REPORT['unsupported'] else 'converted_with_warnings' if REPORT['warnings'] else 'converted'
    text=bpy.data.texts.new('SFM Conversion Report.json');text.write(json.dumps(REPORT,indent=2))
    output=Path(job['output']);output.parent.mkdir(parents=True,exist_ok=True)
    from open_state import prepare_open_state
    prepare_open_state(master,[bpy.data.scenes[strip.scene.name] for strip in strips if strip.type=='SCENE'])
    temporary=output.with_name('.'+output.stem+'.building.blend')
    event('save','Saving Blender project',.96)
    bpy.ops.wm.save_as_mainfile(filepath=str(temporary),check_existing=False)
    if sys.platform=='win32':
        event('save','Collapsing collections in the saved Outliner',.98)
        from outliner_state import finish_file
        try:REPORT['outliner']=finish_file(bpy.app.binary_path,temporary)
        except Exception as exc:
            warn(f'Could not collapse saved Outliner collections: {exc}')
    os.replace(temporary,output)
    report_path=output.with_suffix('.report.json');report_path.write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    event('complete',f'{REPORT["status"]}: {output}',1.)


if __name__=='__main__':
    JOB=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text(encoding='utf-8'))
    REPORT['run_id']=JOB.get('run_id')
    try:convert(JOB)
    except Exception as exc:
        REPORT['status']='failed';REPORT['errors'].append(str(exc));traceback.print_exc()
        Path(JOB['output']).with_suffix('.report.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
        event('failed',str(exc))
        raise
