"""Additional offline sprite state; mathematical approximation of PCF operators.

Unknown operators are rejected by particle_bake.plan, rather than discarded.
Source's random stream, simulation ticks and shader sheets are not reproduced.
"""
import math

def linear_color(value):
    return [c/255/12.92 if c/255<=.04045 else ((c/255+.055)/1.055)**2.4 for c in value[:3]]

def fraction(value,a,b):
    return min(1.,max(0.,(value-a)/(b-a))) if b!=a else float(value>=b)

def sample_yaw_flip(parameters,rng):
    probability=float(parameters.get('Flip Percentage',.5))
    if not math.isfinite(probability) or not 0<=probability<=1:raise ValueError('Invalid particle flip percentage')
    return probability==1 or (probability>0 and rng.random()<probability)

def sprite_uvs(uvs,flip):
    """Mirror within the selected atlas rectangle, never across the whole sheet."""
    return [uvs[i] for i in (1,0,3,2)] if flip else uvs

def remap_scalars(fields,modules,noise_position=None,noise_tables=None):
    """Apply scalar initializers in their PCF order (attribute IDs from Valve SDK)."""
    fields=dict(fields)
    for module in modules:
        p=module['parameters']
        if module['function']=='Remap Noise to Scalar' and p.get('operator enabled',True):
            if noise_position is None:
                raise ValueError('Noise initializer requires an authored birth position')
            from particle_noise_scalar import sample as sample_noise
            if noise_tables is None:
                from particle_noise_emitter import tables
                noise_tables=tables()
            output=int(p.get('output field',3))
            if output not in fields:
                raise ValueError('Noise output is not represented in particle state')
            value=sample_noise(p,noise_position,fields[8],noise_tables)
            # This state adapter represents roll in degrees; PET stores radians.
            fields[output]=math.degrees(value) if output==4 else value
            continue
        if module['function']!='Remap Initial Scalar' or not p.get('operator enabled',True):continue
        creation=fields[8];start=float(p.get('emitter lifetime start time (seconds)',-1));end=float(p.get('emitter lifetime end time (seconds)',-1))
        if (start>=0 and creation<start) or (end>=0 and creation>end):continue
        value=fields[int(p.get('input field',8))];output=int(p.get('output field',3))
        low=float(p.get('input minimum',0));high=float(p.get('input maximum',1))
        if p.get('only active within specified input range',False) and not min(low,high)<=value<=max(low,high):continue
        amount=fraction(value,low,high);a=float(p.get('output minimum',0));b=float(p.get('output maximum',1))
        result=a+(b-a)*amount
        if p.get('output is scalar of initial random range',False):result*=fields[output]
        fields[output]=result
    return fields

def offset_radius(fields,modules,allow_signed_radius=False,noise_position=None,noise_tables=None,stop_index=None):
    """Use radius remaps preceding the offset, rather than the final radius."""
    prefix=[]
    for index,module in enumerate(modules):
        if module['function']=='Position Modify Offset Random' and module['parameters'].get('operator enabled',True) and (stop_index is None or index>=stop_index):break
        prefix.append(module)
    value=remap_scalars(fields,prefix,noise_position,noise_tables)[3]
    if not math.isfinite(value) or (value<0 and not allow_signed_radius):raise ValueError('Invalid particle offset radius')
    return value

def sample(definition,rng,scale,rotation,creation_time=0.,radius=1.,lifetime=1.,particle_id=0,offset_rotation=None,velocity_rotation=None,allow_signed_radius=False,ring_context=None,chaotic_birth=None,sequence_context=None,tint_query=None,cp_vector_query=None):
    from mathutils import Vector
    modules={m['function']:m['parameters'] for m in definition['modules']['initializers'] if m['parameters'].get('operator enabled',True)}
    def vector(bounds_min,bounds_max):return Vector([rng.uniform(float(a),float(b)) for a,b in zip(bounds_min,bounds_max)])
    p=modules.get('Position Within Sphere Random',{})
    # Uniform solid-angle direction, independent of the Source RNG stream.
    z=rng.uniform(-1,1);angle=rng.uniform(0,math.tau)
    direction=Vector((math.sqrt(1-z*z)*math.cos(angle),math.sqrt(1-z*z)*math.sin(angle),z))
    distance=rng.uniform(float(p.get('distance_min',0)),float(p.get('distance_max',0)))
    bias=Vector(p.get('distance_bias',[1,1,1]))
    offset=Vector([direction[i]*distance*bias[i] for i in range(3)])
    absolute=p.get('distance_bias_absolute_value',[0,0,0])
    for i in range(3):
        if absolute[i]:offset[i]=abs(offset[i])
    if p.get('bias in local system',False):offset=rotation@offset
    if 'Position Within Box Random' in modules:
        box=modules['Position Within Box Random']
        offset=vector(box.get('min',[0,0,0]),box.get('max',[0,0,0]))
    velocity=direction*rng.uniform(float(p.get('speed_min',0)),float(p.get('speed_max',0)))
    velocity+=rotation@vector(p.get('speed_in_local_coordinate_system_min',[0,0,0]),p.get('speed_in_local_coordinate_system_max',[0,0,0]))
    if 'Position Along Ring' in modules:
        if ring_context is None:
            raise ValueError('Ring initializer requires birth counter, emission batch size and control-point rotation')
        from particle_ring import settings,transformed_sample
        ring=settings(modules['Position Along Ring'])
        speed=rng.uniform(float(ring['min initial speed']),float(ring['max initial speed']))
        ring_position,ring_velocity=transformed_sample(ring_context['counter'],ring,ring_context['batch_count'],speed,ring_context['rotation'],(0.,0.,0.),random_fraction=None if ring['even distribution'] else rng.random())
        offset=Vector(ring_position);velocity+=Vector(ring_velocity)
    if 'Velocity Random' in modules:
        from particle_velocity import sample as sample_velocity
        world,local=sample_velocity(modules['Velocity Random'],rng)
        velocity+=Vector(world)+(rotation if velocity_rotation is None else velocity_rotation)@Vector(local)
    if 'Position Along Epitrochoid' in modules:
        from particle_epitrochoid import offset as epitrochoid_offset
        parameters=modules['Position Along Epitrochoid']
        offset=Vector(epitrochoid_offset(creation_time,particle_id,parameters))
        if parameters.get('local space',False):offset=rotation@offset
    if 'Position On Spiral Sphere' in modules:
        from particle_spiral_sphere import offset as spiral_offset
        offset=rotation@Vector(spiral_offset(particle_id,modules['Position On Spiral Sphere']))
        rng.random()  # Installed initializer samples initial speed even for zero bounds.
    noise=modules.get('Velocity Noise',{})
    if 'Position From Chaotic Attractor' in modules:
        if chaotic_birth is None:raise ValueError('Chaotic attractor requires ordered context history')
        from particle_chaotic_attractor import velocity as chaotic_velocity
        parameters=modules['Position From Chaotic Attractor']
        prior,following=chaotic_birth
        offset=rotation@Vector(prior)*float(parameters.get('Scale',1))
        speed_unit=rng.random() if float(parameters.get('Speed Max',0))!=0 else 0.
        velocity+=Vector(chaotic_velocity(prior,following,parameters,speed_unit))
    noisy=vector(noise.get('output minimum',[0,0,0]),noise.get('output maximum',[0,0,0]))
    if noise.get('Apply Velocity in Local Space (0/1)',False):noisy=rotation@noisy
    velocity+=noisy
    initializers=definition['modules']['initializers']
    extra_offsets=[]
    for index,module in enumerate(initializers):
        o=module['parameters']
        if module['function']!='Position Modify Offset Random' or not o.get('operator enabled',True):continue
        extra=vector(o.get('offset min',[0,0,0]),o.get('offset max',[0,0,0]))
        if o.get('offset in local space 0/1',False):
            if isinstance(offset_rotation,dict):orientation=offset_rotation.get(index,rotation)
            else:orientation=rotation if offset_rotation is None else offset_rotation
            extra=orientation@extra
        extra_offsets.append((index,o,extra))
    base=definition['parameters'].get('color',[255]*4)
    from particle_distribution import color_bytes
    color=modules.get('Color Random',{})
    outline_rgb=(1.,1.,1.)
    if color.get('output field',6)==22:
        outline_rgb=tuple(v/255 for v in color_bytes(modules,base,rng))
        rgb=linear_color(base)
    elif float(color.get('tint_perc',0))!=0:
        if tint_query is None:raise ValueError('Authored particle tint requires a lighting query')
        from particle_tint_color import color as tinted_color
        rgb=tinted_color(color,base,rng,tint_query)
    else:
        rgb=linear_color(color_bytes(modules,base,rng))
    from particle_cp_vector_color import initialize as initialize_cp_color
    rgb=list(initialize_cp_color(definition['modules']['initializers'],rgb,creation_time,cp_vector_query))
    p=modules.get('Alpha Random',{})
    from particle_distribution import random_float_exp,alpha_bounds
    alpha=random_float_exp(rng,*alpha_bounds(modules,base[3]),p.get('alpha_random_exponent',1))/255
    from particle_distribution import rotation_angle
    angle=rotation_angle(modules,rng)
    p=modules.get('Rotation Speed Random',{})
    spin=float(p.get('rotation_speed_constant',definition['parameters'].get('rotation_speed',0)))+rng.uniform(float(p.get('rotation_speed_random_min',0)),float(p.get('rotation_speed_random_max',0)))
    if p.get('randomly_flip_direction',False) and rng.random()<.5:spin=-spin
    if not math.isfinite(spin):raise ValueError('Invalid particle rotation speed')
    from particle_yaw import sample as sample_yaw
    yaw,yaw_flip=sample_yaw(definition['modules']['initializers'],rng)
    sequence=int(definition['parameters'].get('sequence_number',0))
    sequence_initializers=[(index,module) for index,module in enumerate(definition['modules']['initializers'])
                           if module['function']=='Sequence Random' and module['parameters'].get('operator enabled',True)]
    if sequence_initializers:
        from particle_sequence import SequenceSelection
        for index,module in sequence_initializers:
            parameters=module['parameters']
            context=(sequence_context.get(index) if isinstance(sequence_context,dict) else sequence_context)
            if context is None:
                if parameters.get('shuffle',False) or parameters.get('linear',False):
                    raise ValueError('Sequence mode requires persistent collection context')
                context=SequenceSelection(parameters,rng)
            sequence=context.next()
    trail=modules.get('Trail Length Random',{})
    trail_duration=rng.uniform(float(trail.get('length_min',.1)),float(trail.get('length_max',.1)))
    if not math.isfinite(trail_duration) or trail_duration<0:raise ValueError('Invalid particle trail duration')
    from particle_secondary_sequence import initialize as initialize_secondary
    initial_fields=initialize_secondary(initializers,{1:lifetime,3:radius,4:math.degrees(angle),7:alpha,8:creation_time,9:sequence,10:trail_duration,11:particle_id,12:yaw,13:float(definition['parameters'].get('sequence_number 1',0))},rng)
    fields=remap_scalars(initial_fields,definition['modules']['initializers'])
    for index,o,extra in extra_offsets:
        multiplier=offset_radius(initial_fields,initializers,allow_signed_radius,stop_index=index) if o.get('offset proportional to radius 0/1',False) else 1.
        offset+=extra*multiplier
    if not all(math.isfinite(v) for v in fields.values()) or (fields[3]<0 and not allow_signed_radius) or fields[10]<0:raise ValueError('Invalid remapped particle values')
    force_seed=rng.getrandbits(64) if any(m['parameters'].get('operator enabled',True) for m in definition['modules'].get('forces',[])) else 0
    from particle_scalar_oscillation import sample as sample_oscillation
    oscillations={index:sample_oscillation(m['parameters'],rng) for index,m in enumerate(definition['modules']['operators']) if m['function']=='Oscillate Scalar' and m['parameters'].get('operator enabled',True)}
    from particle_scalar_ramp import sample_operators
    oscillations.update(sample_operators(definition['modules']['operators'],rng))
    from particle_vector_history import sample as sample_vector
    vectors={index:sample_vector(m['parameters'],rng) for index,m in enumerate(definition['modules']['operators']) if m['function']=='Oscillate Vector' and m['parameters'].get('operator enabled',True)}
    return {'offset':offset*scale,'velocity':velocity*scale,'rgb':rgb,'outline_rgb':outline_rgb,'outline_alpha':1.,'alpha':min(1,max(0,fields[7])),'angle':math.radians(fields[4]),'rotation_speed':spin,'yaw':fields[12],'yaw_flip':yaw_flip,'sequence':sequence,'secondary_sequence':int(fields[13]),'trail_duration':fields[10],'radius':fields[3],'force_seed':force_seed,'scalar_oscillations':oscillations,'vector_oscillations':vectors}

def evaluate(definition,state,age,lifetime,scale):
    from mathutils import Vector
    rgb=list(state['rgb']);alpha=state['alpha'];f=age/lifetime
    position=state['offset'].copy();velocity=state['velocity'];angle=state['angle']
    rotation_speed=float(state.get('rotation_speed',definition['parameters'].get('rotation_speed',0)))
    rotation_basic_seen=False
    for index,module in enumerate(definition['modules']['operators']):
        p=module['parameters'];name=module['function']
        if not p.get('operator enabled',True):continue
        if name=='Movement Basic':
            gravity=Vector(p.get('gravity',[0,0,0]))*scale
            drag=max(0.,float(p.get('drag',0)))
            # Analytic linear drag, explicitly approximate relative to Source ticks.
            if drag>1e-8:
                decay=math.exp(-drag*age)
                position+=velocity*((1-decay)/drag)+gravity*(age/drag-(1-decay)/(drag*drag))
            else:position+=velocity*age+gravity*(.5*age*age)
        elif name=='Alpha Fade and Decay':
            incoming=fraction(f,float(p.get('start_fade_in_time',0)),float(p.get('end_fade_in_time',.5)))
            outgoing=fraction(f,float(p.get('start_fade_out_time',.5)),float(p.get('end_fade_out_time',1)))
            alpha*=float(p.get('start_alpha',1))+(1-float(p.get('start_alpha',1)))*incoming
            alpha*=1+(float(p.get('end_alpha',0))-1)*outgoing
        elif name=='Color Fade':
            from particle_color_fade import color as fade_color
            target=linear_color(p.get('color_fade',[255]*4))
            from particle_color_timing import KEYS,History
            if any(float(p.get(k,0))!=0 for k in KEYS):
                histories=state.setdefault('_color_fade_histories',{})
                if index not in histories:histories[index]=History(state['rgb'],target,lifetime,p,state.get('creation_simulation_time',0.))
                rgb=list(histories[index].query(age))
            else:rgb=list(fade_color(state['rgb'],target,f,p))
        elif name=='Rotation Basic':angle+=math.radians(rotation_speed)*age;rotation_basic_seen=True
        elif name=='Remap Scalar' and p.get('output field')==5:
            from particle_rotation_remap import remap_speed,late_write_angle_correction
            updated=remap_speed(p,float(state.get('creation_simulation_time',0.)),rotation_speed)
            angle+=late_write_angle_correction(rotation_speed,updated,age,rotation_basic_seen)
            rotation_speed=updated
        elif name=='Oscillate Scalar' and p.get('oscillation field',7)==4:
            from particle_scalar_oscillation import delta as scalar_oscillation_delta
            angle+=scalar_oscillation_delta(state.get('scalar_oscillations',{}).get(index,p),age,lifetime)
        elif name=='Rotation Spin Roll':
            from particle_spin import angle as spin_angle
            angle+=spin_angle(p,age,state.get('creation_simulation_time',0.))
    if any(m['function']=='Ramp Scalar Linear Random' and m['parameters'].get('ramp field',3)==4 and m['parameters'].get('operator enabled',True) for m in definition['modules']['operators']):
        from particle_roll_history import History
        if '_roll_ramp_history' not in state:
            samples=state.get('scalar_oscillations',{})
            modules=[{**m,'parameters':samples.get(i,m['parameters'])} for i,m in enumerate(definition['modules']['operators'])]
            state['_roll_ramp_history']=History(modules,state['angle'],lifetime,state.get('rotation_speed',0.),state.get('creation_simulation_time',0.))
        angle=state['_roll_ramp_history'].query(age)
    forces=definition['modules'].get('forces',[])
    position_vectors=any(p['oscillation field']==0 for p in state.get('vector_oscillations',{}).values())
    ordered_position=position_vectors or state.get('_ordered_force_history',False)
    if forces and not ordered_position:
        from particle_force_history import ForceHistory
        motion=next((m['parameters'] for m in definition['modules']['operators'] if m['function']=='Movement Basic' and m['parameters'].get('operator enabled',True)),{})
        if '_random_force_history' not in state:
            state['_random_force_history']=ForceHistory(forces,state.get('force_seed',0),float(motion.get('drag',0)))
        position+=Vector(state['_random_force_history'].query(age))*scale
    if state.get('vector_oscillations') or ordered_position:
        from particle_vector_history import History
        if '_vector_history' not in state:
            modules=[]
            for index,module in enumerate(definition['modules']['operators']):
                p=module['parameters'];name=module['function']
                if not p.get('operator enabled',True):continue
                if name=='Oscillate Vector':
                    p=dict(state['vector_oscillations'][index])
                    if p['oscillation field']==0:
                        for key in ('oscillation rate min','oscillation rate max'):p[key]=tuple(v*scale for v in p[key])
                elif name=='Movement Basic' and ordered_position:
                    p={**p,'gravity':tuple(float(v)*scale for v in p.get('gravity',(0.,)*3))}
                elif name=='Color Fade':p={**p,'_collection_birth':state.get('creation_simulation_time',0.)}
                else:continue
                modules.append({'function':name,'parameters':p})
            acceleration=None
            if forces and ordered_position:
                from particle_random_force_history import history as force_history
                force=force_history(forces,state.get('force_seed',0))
                acceleration=lambda time:tuple(v*scale for v in force(time))
            spatial=state.get('_spatial_acceleration')
            if ordered_position and any(m['parameters'].get('operator enabled',True) and
                    m['function']!='random force' for m in forces) and spatial is None:
                raise ValueError('Spatial vector history requires imported control-point context')
            state['_vector_history']=History(modules,state['offset'],state['velocity'],state['rgb'],lifetime,
                                            acceleration=acceleration,spatial_acceleration=spatial)
        received,_,color=state['_vector_history'].query(age)
        if ordered_position:position=Vector(received)
        rgb=list(color)
    return position,rgb,max(0.,min(1.,alpha)),angle
