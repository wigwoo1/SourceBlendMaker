"""Native maintained-count sprite geometry, evaluated without Python handlers.

Emitter count, random lifetime/radius/alpha, offsets, fades and birth replacement
are preserved. Velocity noise is sampled approximately; Source RNG, drag ticks,
atlas sequences and rendering fades remain renderer-specific approximations.
"""
import math,random,json
from particle_random import seed as particle_seed
from particle_sim import simulation_at,shot_segments,delayed_segments

def bake(system,definition,descriptor,shot,scene,frames,seconds,material,curves_factory,scale):
    from particle_names import normalize
    definition=normalize(definition)
    if material.get('sfm_particle_dual_sequence',False):
        raise ValueError('Maintained dual-sequence sprites require lifecycle/UV integration')
    import bpy
    from mathutils import Vector
    from particle_bake import enabled,parameters
    from particle_initial import validate_count
    if validate_count(definition['parameters'].get('initial_particles',0)):
        raise ValueError('Initial particles combined with maintained-count emission are not yet supported')
    allowed={'renderers':{'render_animated_sprites'},'emitters':{'emit to maintain count'},
             'initializers':{'Color Random','Rotation Random','Sequence Random','Velocity Noise','Lifetime Random','Rotation Yaw Flip Random','Alpha Random','Position Modify Offset Random','Position Within Sphere Random','Radius Random'},
             'operators':{'Rotation Basic','Radius Scale','Alpha Fade Out Random','Alpha Fade In Random','Alpha Fade and Decay','Color Fade','Movement Basic','Lifespan Decay'},'forces':set(),'constraints':set()}
    for group,names in allowed.items():
        unsupported=[m['function'] for m in enabled(definition,group) if m['function'] not in names]
        if unsupported:raise ValueError('Unsupported maintained sprites '+group+': '+', '.join(unsupported))
    emitter=parameters(definition,'emitters','emit to maintain count')
    from particle_maintain_count import target_count
    count=target_count(emitter)
    if not 0<count<=10000:raise ValueError('Maintained sprite count must be 1–10000')
    if int(emitter.get('maintain count scale control point',-1))>=0:raise ValueError('Control-point count scaling not implemented')
    life=parameters(definition,'initializers','Lifetime Random');radius=parameters(definition,'initializers','Radius Random')
    sphere=parameters(definition,'initializers','Position Within Sphere Random')
    cp_index=int(sphere.get('control_point_number',0));cp_id=descriptor['control_points'][cp_index]['id']
    control=next(o for o in scene.objects if o.get('sfm_transform_id')==cp_id)
    from particle_control import stationary_origin
    moving=False
    try:origin=stationary_origin(scene,control,frames)
    except ValueError:
        moving=True
        old_frame,old_subframe=scene.frame_current,scene.frame_subframe
        scene.frame_set(int(frames[0]));origin=control.matrix_world.translation.copy()
        scene.frame_set(old_frame,subframe=old_subframe)
    segments=delayed_segments(shot_segments(shot,system,shot.start,shot.start+shot.duration),float(definition.get('child_delay',0)))
    gates=[]
    for segment in segments:
        if not segment.emitting or not segment.simulating:continue
        a=max(float(emitter.get('emission start time',0)),simulation_at(segments,segment.start));b=simulation_at(segments,segment.end)
        if b<=a:continue
        if gates and abs(gates[-1][1]-a)<1e-7:gates[-1]=(gates[-1][0],b)
        else:gates.append((a,b))
    rng=random.Random(particle_seed(descriptor,definition))
    initial={m['function']:m['parameters'] for m in enabled(definition,'initializers')}
    sheet=json.loads(material.get('sfm_particle_sheet','{}'))
    renderer=parameters(definition,'renderers','render_animated_sprites')
    sequence=initial.get('Sequence Random',{})
    from particle_sequence import SequenceSelection
    sequence_context=SequenceSelection(sequence,rng) if 'Sequence Random' in initial else None
    sequence_min=sequence_context.minimum if sequence_context else int(definition['parameters'].get('sequence_number',0))
    sequence_max=sequence_context.maximum if sequence_context else sequence_min
    if sequence_max<sequence_min:raise ValueError('Invalid particle sequence range')
    if sheet:
        for number in range(sequence_min,sequence_max+1):
            if str(number) not in sheet or not sheet[str(number)]['frames']:raise ValueError('Particle sheet has no usable sequence '+str(number))
        if int(renderer.get('orientation_type',0))!=0:raise ValueError('Non-camera-facing maintained atlas sprites are unsupported')
        if float(renderer.get('second sequence animation rate',0))!=0:raise ValueError('Dual-sequence atlas blending is unsupported')
        from particle_sheet_nodes import material_with_sheet_uv
        material=material_with_sheet_uv(material)
    if float(initial.get('Color Random',{}).get('tint_perc',0))!=0:raise ValueError('Lighting/control-point particle color tint is unsupported')
    for operator in enabled(definition,'operators'):
        if operator['function'] in ('Color Fade','Alpha Fade and Decay'):
            p=operator['parameters']
            if any(float(p.get(key,0))!=0 for key in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')):
                raise ValueError('Maintained color/alpha operator strength timing is unsupported')
            if operator['function']=='Color Fade':
                values=[float(p.get('fade_start_time',0)),float(p.get('fade_end_time',1)),*map(float,p.get('color_fade',[255]*4))]
                valid=values[1]>=values[0] and len(values)>=5
            else:
                values=[float(p.get(k,v)) for k,v in (('start_fade_in_time',0),('end_fade_in_time',.5),('start_fade_out_time',.5),('end_fade_out_time',1),('start_alpha',1),('end_alpha',0))]
                valid=values[1]>=values[0] and values[3]>=values[2] and all(0<=v<=1 for v in values[4:])
            if not valid or not all(math.isfinite(v) for v in values):raise ValueError('Invalid maintained color/alpha fade parameters')
        if operator['function']=='Radius Scale':
            p=operator['parameters']
            values=[float(p.get(key,default)) for key,default in (('start_time',0),('end_time',1),('radius_start_scale',1),('radius_end_scale',1))]
            if not all(math.isfinite(v) for v in values) or values[1]<values[0] or min(values[2:])<0:
                raise ValueError('Invalid maintained radius scale range')
        if operator['function']=='Movement Basic':
            p=operator['parameters']
            if not all(math.isfinite(float(v)) for v in [p.get('drag',0),*p.get('gravity',[0,0,0])]):
                raise ValueError('Invalid maintained particle gravity/drag')
    movement=[m['parameters'] for m in enabled(definition,'operators') if m['function']=='Movement Basic']
    if len(movement)>1:raise ValueError('Repeated maintained Movement Basic is unsupported')
    offset=initial.get('Position Modify Offset Random',{});velocity=initial.get('Velocity Noise',{})
    offset_control=None
    if offset.get('offset in local space 0/1',False):
        offset_index=float(offset.get('control_point_number',0))
        if not math.isfinite(offset_index) or offset_index!=int(offset_index) or not 0<=offset_index<64:raise ValueError('Invalid maintained offset control point')
        offset_id=descriptor['control_points'][int(offset_index)]['id']
        offset_control=next(o for o in scene.objects if o.get('sfm_transform_id')==offset_id)
        moving=True
    if sphere.get('bias in local system',False) or velocity.get('Apply Velocity in Local Space (0/1)',False) or any(float(v)!=0 for key in ('speed_in_local_coordinate_system_min','speed_in_local_coordinate_system_max') for v in sphere.get(key,[0,0,0])):moving=True
    alpha=initial.get('Alpha Random',{});color=initial.get('Color Random',{})
    fades={}
    for operator in enabled(definition,'operators'):
        if operator['function'] not in ('Alpha Fade In Random','Alpha Fade Out Random'):continue
        word='in' if operator['function']=='Alpha Fade In Random' else 'out'
        if word in fades:raise ValueError('Repeated alpha fade operators are unsupported')
        p=operator['parameters'];minimum=float(p.get(f'fade {word} time min',.25));maximum=float(p.get(f'fade {word} time max',.25))
        if not all(math.isfinite(value) for value in (minimum,maximum)) or minimum<0 or maximum<minimum:raise ValueError('Invalid alpha fade range')
        if float(p.get(f'fade {word} time exponent',1))!=1:raise ValueError('Biased random alpha fade durations are unsupported')
        fades[word]=(minimum,maximum)
    vertices=[];faces=[];uv_values=[];attributes={key:[] for key in ('life','center','velocity','local_velocity','corner','spawn_offset','sphere_offset','angle','alpha','color',*(f'fade_{word}' for word in fades),*(('sheet_sequence','uv_u','uv_v') if sheet else ()))}
    for index in range(count):
        lifespan=rng.uniform(float(life['lifetime_min']),float(life['lifetime_max']))
        if lifespan<=0:raise ValueError('Invalid particle lifetime')
        r=rng.uniform(float(radius['radius_min']),float(radius['radius_max']))*scale
        offset_factor=r/scale if offset.get('offset proportional to radius 0/1',False) else 1.
        spawn_offset=Vector([rng.uniform(float(offset.get('offset min',[0,0,0])[i]),float(offset.get('offset max',[0,0,0])[i]))*scale*offset_factor for i in range(3)])
        center=origin+spawn_offset
        distance=rng.uniform(float(sphere.get('distance_min',0)),float(sphere.get('distance_max',0)))
        direction=Vector([rng.uniform(-1,1) for _ in range(3)]).normalized()
        bias=sphere.get('distance_bias',[1,1,1]);absolute=sphere.get('distance_bias_absolute_value',[0,0,0])
        if len(bias)!=3 or len(absolute)!=3 or not all(math.isfinite(float(v)) for v in bias):raise ValueError('Invalid maintained sphere bias')
        sphere_offset=Vector([direction[i]*distance*scale*float(bias[i]) for i in range(3)])
        for i in range(3):
            if absolute[i]:sphere_offset[i]=abs(sphere_offset[i])
        center+=sphere_offset
        speed=rng.uniform(float(sphere.get('speed_min',0)),float(sphere.get('speed_max',0)))
        vel=direction*speed*scale
        local_velocity=Vector((0,0,0))
        for i in range(3):
            local_velocity[i]=rng.uniform(float(sphere.get('speed_in_local_coordinate_system_min',[0,0,0])[i]),float(sphere.get('speed_in_local_coordinate_system_max',[0,0,0])[i]))*scale
            noise_velocity=rng.uniform(float(velocity.get('output minimum',[0,0,0])[i]),float(velocity.get('output maximum',[0,0,0])[i]))*scale
            vel[i]+=local_velocity[i]+noise_velocity
            if velocity.get('Apply Velocity in Local Space (0/1)',False):local_velocity[i]+=noise_velocity
        from particle_distribution import alpha_bounds,random_float_exp,color_bytes,rotation_angle
        from particle_sprite_state import linear_color
        base_color=definition['parameters'].get('color',[255]*4)
        opacity=random_float_exp(rng,*alpha_bounds(initial,base_color[3]),alpha.get('alpha_random_exponent',1))/255
        rgb=linear_color(color_bytes(initial,base_color,rng))
        angle=rotation_angle(initial,rng)
        sampled_fades={f'fade_{word}':minimum if minimum==maximum else rng.uniform(minimum,maximum) for word,(minimum,maximum) in fades.items()}
        sampled_sequence=sequence_context.next() if sequence_context else sequence_min
        from particle_sprite_state import sample_yaw_flip,sprite_uvs
        flip=sample_yaw_flip(initial['Rotation Yaw Flip Random'],rng) if 'Rotation Yaw Flip Random' in initial else False
        corners=sprite_uvs([(0,0),(1,0),(1,1),(0,1)],flip);uv_values.extend(corners)
        faces.append(tuple(range(len(vertices),len(vertices)+4)))
        for uv_value,corner in zip(corners,((-r,-r,0),(r,-r,0),(r,r,0),(-r,r,0))):
            vertices.append(center)
            atlas={'sheet_sequence':sampled_sequence,'uv_u':uv_value[0],'uv_v':uv_value[1]} if sheet else {}
            for key,value in {'life':lifespan,'center':center,'velocity':vel,'local_velocity':local_velocity,'corner':corner,'spawn_offset':spawn_offset,'sphere_offset':sphere_offset,'angle':angle,'alpha':opacity,'color':(*rgb,1),**sampled_fades,**atlas}.items():attributes[key].append(value)
    mesh=bpy.data.meshes.new(system.name+' maintained sprites');mesh.from_pydata(vertices,[],faces);mesh.materials.append(material)
    uv=mesh.uv_layers.new()
    for item,value in zip(uv.data,uv_values):item.uv=value
    for name,values in attributes.items():
        kind='FLOAT_VECTOR' if name in ('center','velocity','local_velocity','corner','spawn_offset','sphere_offset') else ('FLOAT_COLOR' if name=='color' else 'FLOAT')
        attr=mesh.attributes.new('sfm_'+name,kind,'POINT')
        for item,value in zip(attr.data,values):
            if kind=='FLOAT_VECTOR':item.vector=value
            elif kind=='FLOAT_COLOR':item.color=value
            else:item.value=value
    obj=bpy.data.objects.new(system.name+' maintained particle effect',mesh);scene.collection.objects.link(obj)
    obj['sfm_particle_effect']=definition['name'];obj['sfm_particle_approximate']=True
    from particle_identity import tag
    tag(obj,definition)
    graph=bpy.data.node_groups.new(system.name+' particle evaluation','GeometryNodeTree')
    graph.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');graph.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    nodes=graph.nodes;links=graph.links
    source=nodes.new('NodeGroupInput');output=nodes.new('NodeGroupOutput')
    def math_node(operation,a,b=0):
        node=nodes.new('ShaderNodeMath');node.operation=operation
        for socket,value in zip(node.inputs,(a,b)):
            if hasattr(value,'node'):links.new(value,socket)
            else:socket.default_value=value
        return node.outputs[0]
    def attribute(name,kind='FLOAT'):
        node=nodes.new('GeometryNodeInputNamedAttribute');node.data_type=kind;node.inputs['Name'].default_value='sfm_'+name;return node.outputs['Attribute']
    clock=nodes.new('ShaderNodeValue');clock.name='Source particle simulation time'
    times=[simulation_at(segments,float(t)) for t in seconds]
    clock.outputs[0].default_value=times[0];curves_factory(graph,system.name+' particle clock').add(clock.outputs[0].path_from_id('default_value'),frames,times)
    lifetime=attribute('life');birth=-1e9
    for a,b in gates:
        capped=math_node('MINIMUM',clock.outputs[0],max(a,b-1e-7))
        cycles=math_node('FLOOR',math_node('DIVIDE',math_node('SUBTRACT',capped,a),lifetime))
        candidate=math_node('ADD',math_node('MULTIPLY',cycles,lifetime),a)
        valid=math_node('GREATER_THAN',clock.outputs[0],a-1e-7)
        candidate=math_node('ADD',math_node('MULTIPLY',candidate,valid),math_node('MULTIPLY',math_node('SUBTRACT',1,valid),-1e9))
        birth=math_node('MAXIMUM',birth,candidate)
    age=math_node('SUBTRACT',clock.outputs[0],birth);fraction=math_node('DIVIDE',age,lifetime)
    def phase(value,a,b):
        f=math_node('DIVIDE',math_node('SUBTRACT',value,a),b-a) if a!=b else math_node('SUBTRACT',1,math_node('LESS_THAN',value,b))
        return math_node('MINIMUM',1,math_node('MAXIMUM',0,f))
    opacity=math_node('MULTIPLY',attribute('alpha'),math_node('LESS_THAN',age,lifetime))
    for module in enabled(definition,'operators'):
        p=module['parameters']
        if module['function'] in ('Alpha Fade In Random','Alpha Fade Out Random'):
            incoming=module['function']=='Alpha Fade In Random';word='in' if incoming else 'out'
            duration=math_node('MAXIMUM',attribute('fade_'+word),1e-7)
            elapsed=fraction if p.get('proportional 0/1',True) else age
            fade=math_node('DIVIDE',elapsed if incoming else math_node('SUBTRACT',1 if p.get('proportional 0/1',True) else lifetime,elapsed),duration)
            fade=math_node('MINIMUM',1,math_node('MAXIMUM',0,fade))
            opacity=math_node('MULTIPLY',opacity,fade)
        elif module['function']=='Alpha Fade and Decay':
            incoming=phase(fraction,float(p.get('start_fade_in_time',0)),float(p.get('end_fade_in_time',.5)))
            outgoing=phase(fraction,float(p.get('start_fade_out_time',.5)),float(p.get('end_fade_out_time',1)))
            start=float(p.get('start_alpha',1));end=float(p.get('end_alpha',0))
            opacity=math_node('MULTIPLY',opacity,math_node('ADD',start,math_node('MULTIPLY',1-start,incoming)))
            opacity=math_node('MULTIPLY',opacity,math_node('ADD',1,math_node('MULTIPLY',end-1,outgoing)))
    opacity=math_node('MINIMUM',1,math_node('MAXIMUM',0,opacity))
    # Analytic linear drag approximation, shared with offline sprite motion.
    motion=movement[0] if movement else {};drag=max(0.,float(motion.get('drag',0)))
    if drag>1e-8:
        decay=math_node('EXPONENT',math_node('MULTIPLY',age,-drag))
        velocity_time=math_node('DIVIDE',math_node('SUBTRACT',1,decay),drag)
        gravity_time=math_node('SUBTRACT',math_node('DIVIDE',age,drag),math_node('DIVIDE',math_node('SUBTRACT',1,decay),drag*drag))
    else:
        velocity_time=age;gravity_time=math_node('MULTIPLY',math_node('MULTIPLY',age,age),.5)
    vector=nodes.new('ShaderNodeVectorMath');vector.operation='SCALE';links.new(attribute('velocity','FLOAT_VECTOR'),vector.inputs[0]);links.new(velocity_time,vector.inputs['Scale'])
    gravity=nodes.new('ShaderNodeVectorMath');gravity.operation='SCALE';gravity.inputs[0].default_value=tuple(float(v)*scale for v in motion.get('gravity',[0,0,0]));links.new(gravity_time,gravity.inputs['Scale'])
    displacement=nodes.new('ShaderNodeVectorMath');displacement.operation='ADD';links.new(vector.outputs['Vector'],displacement.inputs[0]);links.new(gravity.outputs['Vector'],displacement.inputs[1])
    center=nodes.new('ShaderNodeVectorMath');center.operation='ADD';links.new(attribute('center','FLOAT_VECTOR'),center.inputs[0]);links.new(displacement.outputs['Vector'],center.inputs[1])
    angle=attribute('angle')
    for module in enabled(definition,'operators'):
        if module['function']=='Rotation Basic':
            speed=float(definition['parameters'].get('rotation_speed',0))
            if not math.isfinite(speed):raise ValueError('Invalid maintained particle rotation speed')
            angle=math_node('ADD',angle,math_node('MULTIPLY',age,math.radians(speed)))
    corner=attribute('corner','FLOAT_VECTOR')
    for module in enabled(definition,'operators'):
        if module['function']!='Radius Scale':continue
        p=module['parameters'];a=float(p.get('start_time',0));b=float(p.get('end_time',1))
        weight=math_node('DIVIDE',math_node('SUBTRACT',fraction,a),b-a) if b!=a else math_node('SUBTRACT',1,math_node('LESS_THAN',fraction,b))
        weight=math_node('MINIMUM',1,math_node('MAXIMUM',0,weight))
        if p.get('ease_in_and_out',False):
            weight=math_node('MULTIPLY',math_node('MULTIPLY',weight,weight),math_node('SUBTRACT',3,math_node('MULTIPLY',2,weight)))
        start=float(p.get('radius_start_scale',1));end=float(p.get('radius_end_scale',1))
        size=math_node('ADD',start,math_node('MULTIPLY',weight,end-start))
        scaled=nodes.new('ShaderNodeVectorMath');scaled.operation='SCALE';links.new(corner,scaled.inputs[0]);links.new(size,scaled.inputs['Scale']);corner=scaled.outputs['Vector']
    spin=nodes.new('ShaderNodeVectorRotate');spin.rotation_type='AXIS_ANGLE';spin.inputs['Axis'].default_value=(0,0,1);links.new(corner,spin.inputs['Vector']);links.new(angle,spin.inputs['Angle'])
    camera=nodes.new('GeometryNodeObjectInfo');camera.inputs['Object'].default_value=scene.camera;camera.transform_space='ORIGINAL'
    facing=nodes.new('ShaderNodeVectorRotate');facing.rotation_type='EULER_XYZ';links.new(spin.outputs['Vector'],facing.inputs['Vector']);links.new(camera.outputs['Rotation'],facing.inputs['Rotation'])
    position=nodes.new('ShaderNodeVectorMath');position.operation='ADD';links.new(center.outputs['Vector'],position.inputs[0]);links.new(facing.outputs['Vector'],position.inputs[1])
    set_position=nodes.new('GeometryNodeSetPosition');links.new(source.outputs['Geometry'],set_position.inputs['Geometry']);links.new(position.outputs['Vector'],set_position.inputs['Position'])
    combine=nodes.new('FunctionNodeCombineColor');combine.mode='RGB'
    separate=nodes.new('FunctionNodeSeparateColor');links.new(attribute('color','FLOAT_COLOR'),separate.inputs['Color'])
    colors=[separate.outputs[name] for name in ('Red','Green','Blue')]
    from particle_sprite_state import linear_color
    for module in enabled(definition,'operators'):
        if module['function']!='Color Fade':continue
        p=module['parameters'];weight=phase(fraction,float(p.get('fade_start_time',0)),float(p.get('fade_end_time',1)))
        if p.get('ease_in_and_out',False):weight=math_node('MULTIPLY',math_node('MULTIPLY',weight,weight),math_node('SUBTRACT',3,math_node('MULTIPLY',2,weight)))
        target=linear_color(p.get('color_fade',[255]*4))
        colors=[math_node('ADD',color,math_node('MULTIPLY',weight,math_node('SUBTRACT',value,color))) for color,value in zip(colors,target)]
    for name,color in zip(('Red','Green','Blue'),colors):links.new(color,combine.inputs[name])
    links.new(opacity,combine.inputs['Alpha'])
    store=nodes.new('GeometryNodeStoreNamedAttribute');store.data_type='FLOAT_COLOR';store.domain='CORNER';store.inputs['Name'].default_value='sfm_particle_color'
    links.new(set_position.outputs['Geometry'],store.inputs['Geometry']);links.new(combine.outputs['Color'],store.inputs['Value'])
    geometry=store.outputs['Geometry']
    if sheet:
        from particle_sheet_nodes import store_uv
        geometry=store_uv(graph,geometry,age,fraction,sheet,sorted(set(attributes['sheet_sequence'])),renderer,attribute,math_node)
    links.new(geometry,output.inputs['Geometry'])
    modifier=obj.modifiers.new('Source particles','NODES');modifier.node_group=graph
    controls=curves_factory(obj,system.name+' particle visibility')
    hidden=[not bool(shot.value(system,'visible',float(t),True)) for t in seconds]
    for name in ('hide_render','hide_viewport'):setattr(obj,name,hidden[0]);controls.add(name,frames,hidden,interpolation='CONSTANT')
    scene.cycles.transparent_max_bounces=max(scene.cycles.transparent_max_bounces,128)
    if moving:
        from moving_maintained import bake_frames
        return bake_frames(obj,control,origin,system,definition,shot,scene,frames,seconds,segments,gates,curves_factory,offset_control)
    if material.get('sfm_refraction_experimental'):
        from particle_refraction_snapshot import snapshot
        snapshots=snapshot(scene,obj,frames,curves_factory)
        return {'effect':definition['name'],'rendered':True,'geometry_generated':True,'visible_sample_count':sum(not h for h in hidden),'approximate':True,'method':'evaluated maintained refraction frame meshes','frame_meshes':len(snapshots),'particle_slots':count,'limitations':['Source maintained simulation is approximate','Evaluated snapshots increase file size','Refraction compositor installation required']}
    return {'effect':definition['name'],'rendered':True,'geometry_generated':True,'visible_sample_count':sum(not h for h in hidden),'approximate':True,'method':'native maintained sprite geometry nodes','particle_slots':count,'vertices':len(vertices),'emission_gates':gates,'texture_sheet_sequences':len(sheet),'sampled_fade_ranges':{word:list(bounds) for word,bounds in fades.items()},'limitations':['Source RNG/velocity noise and drag ticks are approximate','Slot lifetime/radius/fade/sequence samples repeat across replacement births','Texture sheet playback uses stepped frames; Source playback phase/blending and exact fade easing are not verified','Moving control points are unsupported']}
