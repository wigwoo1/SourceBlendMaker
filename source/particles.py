"""Find mounted Source PCF definitions and inventory their simulation graph."""
import io,json
import itertools
import datamodel

def load_pcf(raw):
    # The DMX parser requires text streams for KeyValues and bytes for binary.
    stream=io.StringIO(raw.decode('utf-8-sig')) if b'encoding keyvalues2' in raw[:128] else io.BytesIO(raw)
    return datamodel.load(in_file=stream)

class ParticleTextureError(ValueError):
    def __init__(self,path,reason):
        self.path=path
        self.category='unsupported_texture_format' if reason.startswith('Unsupported') else 'invalid_texture_data'
        super().__init__(f'{path}: {reason}')

def material_failure(path,exc):
    category=getattr(exc,'category','missing_asset' if isinstance(exc,FileNotFoundError) else 'unsupported_material' if str(exc).startswith('Unsupported particle shader') else 'conversion_error')
    return {'path':path,'converted':False,'failure_category':category,'reason':str(exc)}

def is_system(element):
    return element is not None and element.type.lstrip('C') in ('DmeParticleSystem','DmeGameParticleSystem')

def plain(value):
    if hasattr(value,'id'):return {'id':str(value.id),'name':value.name,'type':value.type}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    if isinstance(value,bytes):return {'binary_bytes':len(value)}
    return value

def material_path(path):
    path=path.replace('\\','/')
    if path.lower().startswith('materials/'):path=path[len('materials/'):]
    return path if path.lower().endswith('.vmt') else path+'.vmt'

def timing_controller(system,parent,shot,frames,seconds,curves_factory):
    import bpy
    controller=bpy.data.objects.new(system.name+' particle controls',None)
    bpy.context.scene.collection.objects.link(controller);controller.parent=parent
    controller['sfm_particle_system_id']=str(system.id)
    curves=curves_factory(controller,system.name+' particle timing')
    attributes=[]
    for attribute,default in (('emitting',True),('simulating',True),('visible',True),('simulationTimeScale',1.0)):
        values=[shot.value(system,attribute,t,system.get(attribute,default)) for t in seconds]
        controller[attribute]=float(values[0])
        curves.add('["'+attribute+'"]',frames,values,interpolation='CONSTANT' if attribute!='simulationTimeScale' else 'LINEAR')
        attributes.append(attribute)
    return {'controller':controller.name,'samples':len(frames),'attributes':attributes}

def sprite_material(assets,path,experimental_refraction=False,scene=None,time_offset=0):
    """Create a native emissive sprite surface; simulation supplies vertex RGBA."""
    import bpy
    from SourceIO.library.source1.vmt import VMT
    from SourceIO.blender_bindings.source1.vtf import import_texture
    path='materials/'+material_path(path)
    buffer=assets.buffer(path)
    if buffer is None:raise FileNotFoundError(path)
    vmt=VMT(buffer,assets.TinyPath(path),assets.cm)
    shader=vmt.shader.lower()
    if shader=='refract' and experimental_refraction:
        from particle_refraction_material import create
        material=create(assets,path,scene,time_offset)
        material['sfm_particle_approximation']='Experimental compositor refraction; Source visual parity and shot phase unverified'
        if material.get('sfm_refraction_limitations'):material['sfm_particle_approximation']+='; '+material['sfm_refraction_limitations']
        return material
    sprite=shader=='sprite'
    sprite_mode=vmt.get_int('$spriterendermode',0) if sprite else None
    if shader not in ('spritecard','unlitgeneric','sprite'):
        raise ValueError(f'Unsupported particle shader {vmt.shader}: {path}')
    if sprite and sprite_mode not in (1,2,4,5):
        raise ValueError(f'Unsupported particle shader Sprite render mode {sprite_mode}: {path}')
    texture=vmt.get_string('$basetexture','')
    image=None;sheet={};recovery=None
    if texture:
        texture=texture.replace('\\','/')
        if not texture.lower().startswith('materials/'):texture='materials/'+texture
        if not texture.lower().endswith('.vtf'):texture+='.vtf'
        data=assets.buffer(texture)
        if data is None:raise FileNotFoundError(texture)
        from particle_sheet import parse_vtf
        data.seek(0)
        try:
            from particle_texture_recovery import payload
            raw,recovery=payload(data.read());sheet=parse_vtf(raw)
        except ValueError as exc:raise ParticleTextureError(texture,str(exc)) from exc
        from SourceIO.library.utils import MemoryBuffer
        data=MemoryBuffer(raw)
        if recovery:print('WARNING: Recovered embedded particle texture '+texture+' after '+str(recovery['removed_prefix_bytes'])+' prefix bytes; original asset unchanged',flush=True)
        image=import_texture(assets.TinyPath(texture),data);image.pack()
    elif vmt.shader.lower()!='unlitgeneric':raise ValueError(f'Particle material has no base texture: {path}')
    material=bpy.data.materials.new(path+' particle');material.use_nodes=True;material.use_fake_user=True
    material['sfm_particle_material']=path;material['sfm_particle_shader']=vmt.shader
    # These geometry flags belong to the VMT, not the PCF renderer parameters.
    # Preserve authored values for diagnostics and spline geometry conversion.
    if shader=='spritecard':
        material['sfm_particle_material_orientation']=vmt.get_int('$orientation',0)
        material['sfm_particle_material_orientation_matrix']=vmt.get_string('$orientationmatrix','')
        material['sfm_particle_material_spline_type']=vmt.get_int('$splinetype',0)
        # Installed SpriteCard setup defaults both endpoint multipliers to one.
        material['sfm_particle_material_alpha_trail_fade']=vmt.get_float('$alphatrailfade',1.)
        material['sfm_particle_material_radius_trail_fade']=vmt.get_float('$radiustrailfade',1.)
        material['sfm_particle_dual_sequence']=bool(vmt.get_int('$dualsequence',0))
        if material['sfm_particle_dual_sequence']:
            if material['sfm_particle_material_spline_type']:
                raise ValueError('Dual-sequence spline materials require separate renderer integration')
            if vmt.get_string('$basetexture2','') or vmt.get_float('$addbasetexture2',0)!=0:
                raise ValueError('Dual-sequence additional base textures remain unsupported')
            crop,_=vmt.get_vector('$crop',(1.,1.))
            if vmt.get_int('$extractgreenalpha',0) or vmt.get_string('$colorramp','') or any(float(v)!=1 for v in crop):
                raise ValueError('Dual-sequence green-alpha, color-ramp or crop material flags remain unsupported')
            mode=vmt.get_int('$sequence_blend_mode',0)
            if mode not in (0,1,2):raise ValueError('Unsupported dual-sequence blend mode')
            if vmt.get_int('$maxlumframeblend1',0):
                raise ValueError('Dual-sequence max-luminance frame blending remains unsupported')
            from particle_dual_sequence_uv import scale_parameters
            zoom=vmt.get_float('$zoomanimateseq2',1.)
            scale_parameters(zoom)
            material['sfm_particle_sequence_blend_mode']=mode
            material['sfm_particle_blend_frames']=bool(vmt.get_int('$blendframes',1))
            material['sfm_particle_maxlum_frame_blend1']=vmt.get_int('$maxlumframeblend1',0)
            material['sfm_particle_authored_maxlum_frame_blend2']=vmt.get_int('$maxlumframeblend2',0)
            material['sfm_particle_sequence_zoom']=zoom
    from particle_distance_alpha import settings as distance_settings
    distance_config=distance_settings(vmt) if shader=='spritecard' else None
    if distance_config:material['sfm_particle_distance_alpha']=json.dumps(distance_config)
    material['sfm_particle_sheet']=json.dumps(sheet)
    if recovery:material['sfm_particle_texture_recovery']=json.dumps({'texture':texture,**recovery})
    material['sfm_particle_approximation']='Sprite shading; sheet playback/blending, depth intersections and screen-size fades are approximate or unsupported'
    if shader=='spritecard' and material['sfm_particle_material_spline_type']:
        material['sfm_particle_approximation']+='; Source spline vertex-shader orientation and signed-width geometry are not verified'
    additive=(sprite and sprite_mode==5) or (not sprite and vmt.get_int('$additive',0))
    # EEVEE's dithered surface mode dropped the emission-plus-transparent
    # shader used for Source additive sprites. BLENDED preserves those
    # particle surfaces in EEVEE; other particle materials keep dithered mode.
    material.surface_render_method='BLENDED' if additive else 'DITHERED'
    tree=material.node_tree;tree.nodes.clear();nodes=tree.nodes;links=tree.links
    if image:
        if material.get('sfm_particle_dual_sequence',False):
            from particle_dual_sequence_material import sample_nodes
            texture_color,texture_alpha=sample_nodes(tree,image,material['sfm_particle_sequence_blend_mode'],material['sfm_particle_blend_frames'])
            material['sfm_particle_approximation']='Decoded dual-sequence table/zoom/blend; Source RNG/ticks, filtering and depth/screen fades remain approximate or unverified'
        else:
            tex=nodes.new('ShaderNodeTexImage');tex.image=image
            texture_color=tex.outputs['Color'];texture_alpha=tex.outputs['Alpha']
    else:
        tex=nodes.new('ShaderNodeRGB');tex.outputs[0].default_value=(1,1,1,1);texture_color=tex.outputs[0]
        opacity=nodes.new('ShaderNodeValue');opacity.outputs[0].default_value=1;texture_alpha=opacity.outputs[0]
    material_color,kind=vmt.get_vector('$color',(1,1,1));material_color=list(material_color)[:3]
    if len(material_color)==1:material_color*=3
    if len(material_color)!=3:raise ValueError('Invalid particle material color')
    if kind is int:material_color=[v/255 for v in material_color]
    base=nodes.new('ShaderNodeMixRGB');base.blend_type='MULTIPLY';base.inputs[0].default_value=1
    links.new(texture_color,base.inputs[1]);base.inputs[2].default_value=(*material_color,1)
    color=nodes.new('ShaderNodeVertexColor');color.layer_name='sfm_particle_color'
    tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
    links.new(base.outputs[0],tint.inputs[1]);tint.inputs[2].default_value=(1,1,1,1)
    spritecard=vmt.shader.lower()=='spritecard'
    use_sprite_vertex=sprite and (sprite_mode!=5 or not vmt.get_int('$ignorevertexcolors',1))
    if spritecard or use_sprite_vertex or (not sprite and vmt.get_int('$vertexcolor',0)):links.new(color.outputs['Color'],tint.inputs[2])
    emission_color=tint.outputs[0]
    if distance_config:
        from particle_distance_alpha import nodes as distance_nodes
        emission_color,texture_alpha=distance_nodes(tree,emission_color,texture_alpha,distance_config)
    alpha=nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY'
    links.new(texture_alpha,alpha.inputs[0]);alpha.inputs[1].default_value=1
    if spritecard or use_sprite_vertex or (not sprite and vmt.get_int('$vertexalpha',0)):links.new(color.outputs['Alpha'],alpha.inputs[1])
    material_alpha=nodes.new('ShaderNodeMath');material_alpha.operation='MULTIPLY';material_alpha.inputs[1].default_value=vmt.get_float('$alpha',1)
    links.new(alpha.outputs[0],material_alpha.inputs[0]);alpha_output=material_alpha.outputs[0]
    emission=nodes.new('ShaderNodeEmission');links.new(emission_color,emission.inputs['Color'])
    strength=float(vmt.get_float('$overbrightfactor',1)) if spritecard else 1
    gain=float(getattr(assets,'particle_light_gain',1.))
    strength*=gain
    material['sfm_particle_light_gain']=gain
    emission.label='Particle glow — illuminates nearby surfaces in Cycles'
    emission.inputs['Strength'].default_value=strength
    transparent=nodes.new('ShaderNodeBsdfTransparent')
    output=nodes.new('ShaderNodeOutputMaterial')
    if additive:
        power=nodes.new('ShaderNodeMath');power.operation='MULTIPLY';power.inputs[1].default_value=strength
        links.new(alpha_output,power.inputs[0]);links.new(power.outputs[0],emission.inputs['Strength'])
        combine=nodes.new('ShaderNodeAddShader')
        links.new(transparent.outputs[0],combine.inputs[0]);links.new(emission.outputs[0],combine.inputs[1])
    else:
        combine=nodes.new('ShaderNodeMixShader');links.new(alpha_output,combine.inputs[0])
        links.new(transparent.outputs[0],combine.inputs[1]);links.new(emission.outputs[0],combine.inputs[2])
    links.new(combine.outputs[0],output.inputs['Surface'])
    return material

class Definitions:
    def __init__(self,assets):self.assets=assets;self.loaded={};self.errors=[];self.missing=set();self.hint_failures={}

    def lookup_summary(self):
        return {'parsed_pcf_files':len(self.loaded),'definition_names':len({name for group in self.loaded.values() for name in group}),
                'unresolved_names':sorted(self.missing),'parse_errors':list(self.errors)}

    def resources(self,paths):
        """Read originals and resolved material textures from the selected mounts."""
        from SourceIO.library.source1.vmt import VMT
        pending=list(paths);seen=set()
        texture_keys=('$basetexture','$basetexture2','$bumpmap','$normalmap','$detail',
                      '$envmapmask','$phongexponenttexture','$blendmodulatetexture')
        while pending:
            path=pending.pop(0).replace('\\','/').lstrip('/')
            if path.lower().endswith(('.vmt','.vtf')) and not path.lower().startswith('materials/'):
                path='materials/'+path
            if path.lower() in seen:continue
            seen.add(path.lower())
            buffer=self.assets.buffer(path)
            if buffer is None:
                yield path,None
                continue
            buffer.seek(0);raw=buffer.read()
            yield path,raw
            if path.lower().endswith('.vmt'):
                buffer.seek(0)
                material=VMT(buffer,self.assets.TinyPath(path),self.assets.cm)
                include=material.get_string('include','')
                if include:pending.append(include if include.lower().endswith('.vmt') else include+'.vmt')
                for key in texture_keys:
                    value=material.get_string(key,'')
                    if value and not value.startswith('_rt_'):
                        pending.append(value if value.lower().endswith('.vtf') else value+'.vtf')
    def find(self,name):
        if name.lower() in self.missing:raise FileNotFoundError(f'Particle definition not found in mounted PCFs: {name}')
        for path,definitions in self.loaded.items():
            if name.lower() in definitions:return path,definitions[name.lower()]
        seen=set(self.loaded)
        scanned=0
        print(f'Particle lookup: searching mounted PCFs for {name}',flush=True)
        # Workshop effects commonly live under particles/<pack>/<effect>.pcf.
        # Keep the flat pattern too: archive globbers do not all interpret ** alike.
        for path,buffer in itertools.chain(self.assets.cm.glob('particles/*.pcf'),self.assets.cm.glob('particles/**/*.pcf')):
            path=str(path)
            if path in seen:
                if hasattr(buffer,'close'):buffer.close()
                continue
            seen.add(path)
            scanned+=1
            if scanned==1 or scanned%25==0:
                print(f'Particle lookup: {name}, scanning file {scanned}: {path}',flush=True)
            try:
                if buffer is None:continue
                buffer.seek(0);model=load_pcf(buffer.read())
                definitions={e.name.lower():e for e in model.root.get('particleSystemDefinitions',[])}
                self.loaded[path]=definitions
                if name.lower() in definitions:return path,definitions[name.lower()]
            except Exception as exc:self.errors.append(f'{path}: {exc}')
            finally:
                if hasattr(buffer,'close'):buffer.close()
        self.missing.add(name.lower())
        raise FileNotFoundError(f'Particle definition not found in mounted PCFs: {name}')

    def describe(self,system,pcf_paths=()):
        from particle_paths import recorded_pcf_path
        hints=[recorded_pcf_path(p) for p in pcf_paths]
        hint_results=[]
        for hint in hints:
            if hint in self.loaded:
                hint_results.append({'path':hint,'parsed':True});continue
            if hint in self.hint_failures:
                hint_results.append(dict(self.hint_failures[hint]));continue
            buffer=self.assets.buffer(hint)
            if buffer is None:
                failure={'path':hint,'parsed':False,'reason':'Recorded PCF not found in selected mounts'}
                self.hint_failures[hint]=failure;hint_results.append(dict(failure));continue
            try:
                buffer.seek(0);model=load_pcf(buffer.read())
                definitions={e.name.lower():e for e in model.root.get('particleSystemDefinitions',[])}
                self.loaded[hint]=definitions;self.missing.difference_update(definitions)
                hint_results.append({'path':hint,'parsed':True})
            except Exception as exc:
                failure={'path':hint,'parsed':False,'reason':str(exc)}
                self.hint_failures[hint]=failure;hint_results.append(dict(failure))
            finally:
                if hasattr(buffer,'close'):buffer.close()
        definition=system.get('particleSystemDefinition');path=None
        if definition is None:
            try:path,definition=self.find(system.get('particleSystemType',system.name))
            except FileNotFoundError as exc:
                failures=[r['path']+': '+r['reason'] for r in hint_results if not r['parsed']]
                if failures:raise FileNotFoundError(str(exc)+'; recorded PCFs: '+'; '.join(failures)) from None
                raise
        definitions=[];dependencies=set(hints);occurrences={}
        def strings(value):
            if isinstance(value,str):
                normalized=value.replace('\\','/')
                if normalized.lower().endswith(('.vmt','.mdl','.vtf','.vsnap')):dependencies.add(normalized)
            elif isinstance(value,(list,tuple)):
                for item in value:strings(item)
        def walk(element,delay=0.,end_cap=False,ancestry=(),parent_instance=None,link_parameters=None):
            identity=str(element.id)
            if identity in ancestry:raise ValueError('Cyclic particle child graph: '+element.name)
            if len(definitions)>=10000:raise ValueError('Particle child graph exceeds 10000 instances')
            ancestry=(*ancestry,identity);modules={}
            for group in ('renderers','emitters','initializers','operators','forces','constraints'):
                modules[group]=[]
                for operator in element.get(group,[]):
                    modules[group].append({'function':operator.get('functionName',operator.name),'parameters':{k:plain(v) for k,v in operator.items()}})
                    for v in operator.values():strings(v)
            parameters={k:plain(v) for k,v in element.items() if k not in (*modules,'children')}
            if parameters.get('material'):
                parameters['material']=material_path(parameters['material']);dependencies.add(parameters['material'])
            for v in element.values():strings(v)
            children=[c.get('child') for c in element.get('children',[]) if c.get('child') is not None]
            instance=len(definitions)
            occurrence=occurrences.get(identity,0);occurrences[identity]=occurrence+1
            definitions.append({'name':element.name,'instance_id':instance,'parent_instance_id':parent_instance,'child_link_parameters':link_parameters or {},'random_instance_index':occurrence,'parameters':parameters,'modules':modules,'children':[c.name for c in children],
                                'child_delay':delay,'end_cap_effect':end_cap})
            for link in element.get('children',[]):
                child=link.get('child')
                if child is not None:walk(child,delay+float(link.get('delay',0)),end_cap or bool(link.get('end cap effect',False)),ancestry,instance,{k:plain(v) for k,v in link.items() if k!='child'})
        walk(definition)
        return {'system':system.name,'effect':definition.name,'pcf':path,'recorded_pcf_files':hint_results,'random_seed':system.get('randomSeed'),
                'simulation_flags':{k:system.get(k) for k in ('simulating','emitting','simulationTimeScale','visible')},
                'control_points':plain(system.get('controlPoints',[])),'control_models':plain(system.get('controlModels',[])),
                'definitions':definitions,'dependencies':sorted(dependencies),'rendered':False}
