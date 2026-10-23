"""Native per-frame sprite geometry for the supported PCF operator subset.

No handlers or external caches are required after saving. This is explicitly
approximate: Source random streams, engine ticks and renderer fades differ.
"""
import math,random,json
import time as wall_clock
from particle_random import seed as particle_seed
from particle_sim import shot_segments,continuous_births,living,emission_window,delayed_segments

def enabled(definition,group):
    return [m for m in definition['modules'][group] if m['parameters'].get('operator enabled',True)]

def parameters(definition,group,function):
    items=[m['parameters'] for m in enabled(definition,group) if m['function']==function]
    if not items:raise ValueError(f'Missing required {function} initializer/operator')
    if len(items)>1:raise ValueError(f'Repeated {function} initializer/operator ({len(items)} instances): ordered writes and random sampling are unsupported')
    return items[0]

def plan(definition,sheet=None,experimental_decay=False,experimental_ring=False,experimental_partial_lock=False,allow_tint=False,allow_burst_scaling=False,material=None):
    from particle_names import normalize
    definition=normalize(definition)
    from particle_renderers import passes
    render_passes=passes(definition)
    if len(render_passes)>1:
        plans=[plan(d,sheet,experimental_decay=experimental_decay,experimental_ring=experimental_ring,experimental_partial_lock=experimental_partial_lock,allow_tint=allow_tint,allow_burst_scaling=allow_burst_scaling,material=material) for d in render_passes]
        return {**plans[0],'renderer':'multiple','renderer_plans':plans}
    allowed={'renderers':{'render_animated_sprites','render_sprite_trail','render_rope'},'emitters':{'emit_continuously','emit_instantaneously','emit to maintain count','emit noise'},
             'initializers':{'Radius Random','Lifetime Random','lifetime from sequence','Position From Control Points','Position Along Path Sequential','Rotation Random','Rotation Yaw Random','Rotation Speed Random','Rotation Yaw Flip Random','Position Within Sphere Random','Position Within Box Random','Position Modify Offset Random','Position Modify Warp Random','Color Random','Alpha Random','Sequence Random','Trail Length Random','Velocity Noise','Velocity Random','Remap Initial Scalar'},
             'operators':{'Remap Scalar','Radius Scale','Alpha Fade In Random','Alpha Fade Out Random','Alpha Fade In Simple','Alpha Fade Out Simple','Alpha Fade and Decay','Movement Basic','Movement Lock to Control Point','Lifespan Decay','Color Fade','Rotation Basic','Rotation Spin Roll','Oscillate Scalar Simple'},'forces':{'random force'},'constraints':{'Prevent passing through a plane'}}
    allowed['operators'].update(('Oscillate Scalar','Ramp Scalar Linear Random'))
    allowed['operators'].add('Oscillate Vector')
    if experimental_ring:
        if any(m['function']!='render_rope' for m in enabled(definition,'renderers')):
            raise ValueError('Experimental ring normals require the spline rope renderer')
        allowed['initializers'].update(('Position Along Ring','Normal Align to CP','Normal Modify Offset Random'))
        allowed['operators'].add('Normal Lock to Control Point')
        for module in enabled(definition,'operators'):
            if module['function']=='Remap Direction to CP to Vector':
                if float(module['parameters'].get('output field',0))!=21:
                    raise ValueError('Experimental spline remap supports only installed normal field 21')
                allowed['operators'].add('Remap Direction to CP to Vector')
    # Random zero-thickness rings also work with ordinary sprite renderers.
    allowed['initializers'].add('Position Along Ring')
    allowed['initializers'].add('Position Along Epitrochoid')
    allowed['initializers'].add('Position On Spiral Sphere')
    allowed['initializers'].add('Position From Chaotic Attractor')
    allowed['forces'].add('Force based on distance from plane')
    allowed['forces'].add('twist around axis')
    allowed['operators'].add('Color Light from Control Point')
    allowed['operators'].add('Set Control Point Positions')
    allowed['operators'].add('Cull when crossing plane')
    allowed['initializers'].add('Remap Control Point to Vector')
    allowed['initializers'].add('Sequence Two Random')
    for cull_module in enabled(definition,'operators'):
        if cull_module['function']=='Cull when crossing plane':
            from particle_cull_plane import settings as cull_settings
            cull_settings(cull_module['parameters'])
    for group,names in allowed.items():
        unsupported=[m['function'] for m in enabled(definition,group) if m['function'] not in names]
        if unsupported:raise ValueError('Unsupported '+group+': '+', '.join(unsupported))
    renderers=enabled(definition,'renderers');emitters=enabled(definition,'emitters')
    if len(renderers)!=1:raise ValueError('Requires exactly one supported renderer')
    if material is not None and material.get('sfm_particle_distance_alpha') and renderers[0]['function']!='render_animated_sprites':
        raise ValueError('Distance-alpha outlines currently require animated-sprite geometry')
    if enabled(definition,'constraints'):
        if renderers[0]['function']!='render_animated_sprites':raise ValueError('Sampled plane constraints currently require sprite particles')
        from particle_plane import settings as plane_settings
        for module in enabled(definition,'constraints'):plane_settings(module['parameters'])
    from particle_initial import validate_count
    initial_count=validate_count(definition['parameters'].get('initial_particles',0))
    if any(m['function']=='emit to maintain count' for m in emitters):
        if initial_count:raise ValueError('Initial particles with maintained emission are unsupported')
        if any(m['function']=='lifetime from sequence' or (m['function']=='Remap Initial Scalar' and int(m['parameters'].get('output field',3))==1) for m in enabled(definition,'initializers')):
            raise ValueError('Maintained emission with remapped lifetime is unsupported')
    emitter=emitters[0]['parameters'] if emitters else {}
    emitter_function=('multiple' if len(emitters)>1 else emitters[0]['function']) if emitters else 'initial_particles_only'
    if not emitters and not initial_count:raise ValueError('No emitter or initial particles to create geometry')
    lifetime_modules=[m['parameters'] for m in enabled(definition,'initializers') if m['function']=='Lifetime Random']
    lifetime_samples=[]
    for p in lifetime_modules:
        bounds=[float(p.get('lifetime_min',0)),float(p.get('lifetime_max',0))]
        exponent=float(p.get('lifetime_random_exponent',1))
        if not all(math.isfinite(v) for v in bounds+[exponent]) or min(bounds)<0 or exponent<=0:
            raise ValueError('Invalid ordered Lifetime Random parameters')
        lifetime_samples.append({'bounds':bounds,'exponent':exponent})
    if len(lifetime_modules)>1:
        for p in lifetime_modules:
            if any(float(p.get(key,1))!=1 for key in ('operator time scale min','operator time scale max','operator strength random scale min','operator strength random scale max')):
                raise ValueError('Repeated lifetime randomized strength/time scaling is unverified')
        names=[m['function'] for m in enabled(definition,'initializers')]
        if any(name in names for name in ('Remap Initial Scalar','lifetime from sequence')):
            raise ValueError('Repeated lifetime with intervening lifetime readers/writers is unverified')
    # Installed definition unpack table: lifetime at +0x3ac, default "1.0".
    # Collection initialization copies it into field 1 before initializers run.
    # An absent initializer consumes no lifetime random samples.
    definition_lifetime=float(definition['parameters'].get('lifetime',1.)) if not lifetime_modules else None
    life=lifetime_modules[-1] if lifetime_modules else {
        'lifetime_min':definition_lifetime,'lifetime_max':definition_lifetime}
    # Installed Lifetime Random unpack table: endpoints 0, exponent 1.
    life={'lifetime_min':0.,'lifetime_max':0.,'lifetime_random_exponent':1.,**life}
    radius=next((m['parameters'] for m in enabled(definition,'initializers') if m['function']=='Radius Random'),{'radius_min':definition['parameters'].get('radius',1),'radius_max':definition['parameters'].get('radius',1)})
    # Installed Source Radius Random unpack defaults: all three are 1.
    radius={'radius_min':1.,'radius_max':1.,'radius_random_exponent':1.,**radius}
    positions=[m for m in enabled(definition,'initializers') if m['function'] in ('Position From Control Points','Position Along Path Sequential','Position Within Sphere Random','Position Within Box Random','Position Along Ring','Position Along Epitrochoid','Position On Spiral Sphere','Position From Chaotic Attractor')]
    if len(positions)!=1:raise ValueError('Requires exactly one supported position initializer')
    initializers=enabled(definition,'initializers')
    warps=[i for i,m in enumerate(initializers) if m['function']=='Position Modify Warp Random']
    if warps:
        spatial_names={'Position From Control Points','Position Along Path Sequential','Position Within Sphere Random','Position Within Box Random','Position Along Ring','Position Along Epitrochoid','Position On Spiral Sphere','Position From Chaotic Attractor','Position Modify Offset Random','Velocity Random','Velocity Noise'}
        first_warp=min(warps)
        if any(m['function'] in spatial_names for m in initializers[first_warp+1:]):
            raise ValueError('Position warp after a position or velocity initializer requires ordered history')
        from particle_warp import settings as warp_settings
        for module in enabled(definition,'initializers'):
            if module['function']=='Position Modify Warp Random':warp_settings(module['parameters'])
    position=positions[0]['parameters']
    ring=None
    if positions[0]['function']=='Position From Chaotic Attractor':
        from particle_chaotic_attractor import validate as validate_chaotic
        position=dict(position,control_point_number=validate_chaotic(position))
    if positions[0]['function']=='Position On Spiral Sphere':
        from particle_spiral_sphere import validate as validate_spiral
        position=dict(position,control_point_number=validate_spiral(position))
    if positions[0]['function']=='Position Along Epitrochoid':
        from particle_epitrochoid import validate as validate_epitrochoid
        position=dict(position,control_point_number=validate_epitrochoid(position))
    if positions[0]['function']=='Position Along Ring':
        from particle_ring import settings as ring_settings,identity_sample
        ring=ring_settings(position)
        if ring['even distribution'] and not experimental_ring:
            raise ValueError('Even ring initialization requires experimental spline support')
        # Explicit count avoids claiming installed per-tick batch boundaries.
        if ring['even distribution'] and float(ring['even distribution count'])<=0:
            raise ValueError('Experimental ring requires an explicit positive distribution count')
        if ring['even distribution']:
            identity_sample(0,dict(ring,pitch=0,yaw=0,roll=0),1,ring['min initial speed'])
        else:
            from particle_ring import transformed_sample,angle_matrix
            transformed_sample(0,ring,1,ring['min initial speed'],angle_matrix(0,0,0),(0,0,0),random_fraction=.5)
        if any(m['function']=='Oscillate Scalar Simple' and int(m['parameters'].get('oscillation field',7))==3 for m in enabled(definition,'operators')):
            raise ValueError('Signed ring radius oscillation is unverified')
    path_control=None
    if positions[0]['function']=='Position Along Path Sequential':
        from particle_path import validate
        _,path_start,path_end=validate(position);path_control={'parameters':position,'start':path_start,'end':path_end}
    for group in ('initializers','operators'):
        names=[m['function'] for m in enabled(definition,group)]
        repeatable=('Remap Initial Scalar','Oscillate Scalar Simple','Lifetime Random','Remap Control Point to Vector','Position Modify Warp Random','Position Modify Offset Random','Sequence Random','Sequence Two Random') if group=='initializers' else ('Ramp Scalar Linear Random','Remap Scalar','Oscillate Scalar Simple','Oscillate Scalar','Oscillate Vector','Radius Scale','Rotation Basic')
        unique=[name for name in names if name not in repeatable]
        if len(unique)!=len(set(unique)):raise ValueError('Repeated '+group+' are unsupported')
    for module in enabled(definition,'initializers'):
        p=module['parameters']
        if module['function']=='Sequence Two Random':
            from particle_secondary_sequence import bounds as secondary_bounds
            secondary_bounds(p)
            if any(float(p.get(k,0))!=0 for k in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')):
                raise ValueError('Secondary sequence initializer strength timing remains unverified')
        if module['function']=='Remap Control Point to Vector':
            from particle_cp_vector_color import settings as cp_vector_settings
            cp_vector_settings(p)
        if module['function']=='Velocity Random':
            from particle_velocity import validate as validate_velocity
            validate_velocity(p)
        if module['function']=='Position Within Box Random':
            if any(len(p.get(key,[0,0,0]))!=3 or not all(math.isfinite(float(c)) for c in p.get(key,[0,0,0])) for key in ('min','max')):raise ValueError('Invalid particle box bounds')
        if module['function']=='Remap Initial Scalar' and (int(p.get('input field',8)) not in (1,3,4,7,8,9,10,11) or int(p.get('output field',3)) not in (3,4,7,10)):raise ValueError('Unsupported scalar remap field')
        if module['function']=='Color Random':
            if p.get('output field',6) not in (6,22):raise ValueError('Color Random supports RGB and glow RGB fields 6/22')
            if p.get('output field',6)==22 and float(p.get('tint_perc',0))!=0:raise ValueError('Tinted glow RGB requires separate lighting integration')
        if module['function']=='Color Random' and float(p.get('tint_perc',0))!=0:
            if not allow_tint:raise ValueError('Control-point particle tint is unsupported')
            from particle_tint_color import validate as validate_tint
            validate_tint(p)
        if module['function']=='Position Modify Offset Random':
            cp_offset=float(p.get('control_point_number',0))
            if not math.isfinite(cp_offset) or cp_offset!=int(cp_offset) or not 0<=cp_offset<64:raise ValueError('Invalid particle offset control point')
            if any(len(p.get(key,[0,0,0]))!=3 or not all(math.isfinite(float(c)) for c in p.get(key,[0,0,0])) for key in ('offset min','offset max')):raise ValueError('Invalid particle offset bounds')
        if module['function']=='Position Within Sphere Random':
            from particle_sphere_distribution import settings as sphere_distribution_settings
            sphere_distribution_settings(p)
        for key,value in p.items():
            if (module['function'],key) in (('Alpha Random','alpha_random_exponent'),('Lifetime Random','lifetime_random_exponent'),('Radius Random','radius_random_exponent')):
                if not math.isfinite(float(value)) or float(value)<=0:raise ValueError('Invalid particle distribution exponent: '+key)
                continue
            if key.endswith('exponent') and float(value)!=1:raise ValueError('Biased particle distribution is unsupported: '+key)
    for module in enabled(definition,'operators'):
        if module['function']=='Set Control Point Positions':
            from particle_cp_positions import settings as cp_position_settings
            cp_position_settings(module['parameters'])
        if module['function']=='Color Fade':
            from particle_color_fade import settings as color_fade_settings
            color_fade_settings(module['parameters'])
            from particle_color_timing import settings as color_timing_settings
            color_timing_settings(module['parameters'])
        p=module['parameters']
        if module['function']=='Oscillate Vector':
            from particle_vector_history import settings as vector_settings
            vector=vector_settings(p)
            if vector['oscillation field']==0:
                if any(m['function']=='Movement Lock to Control Point' for m in enabled(definition,'operators')):
                    raise ValueError('Vector position oscillation with control-point locks requires ordered lock history')
                if any(m['function'] not in ('random force','twist around axis','Force based on distance from plane') for m in enabled(definition,'forces')):
                    raise ValueError('Vector position oscillation with spatial forces requires ordered force history')
                if any(not 0<=float(m['parameters'].get('drag',0))<=.9999 for m in enabled(definition,'operators') if m['function']=='Movement Basic'):
                    raise ValueError('Vector movement drag outside checked finite range [0,.9999]')
            elif any(m['function']=='Color Light from Control Point' for m in enabled(definition,'operators')):
                raise ValueError('RGB vector oscillation with control-point lighting requires ordered lighting history')
        if module['function']=='Color Light from Control Point':
            from particle_color_lights import settings as color_light_settings
            color_light_settings(p)
        if module['function']=='Remap Scalar':
            required=('input field','output field','input minimum','input maximum','output minimum','output maximum')
            if any(key not in p for key in required):raise ValueError('Scalar remap requires explicit fields and bounds')
            if any(isinstance(p[key],bool) or not isinstance(p[key],(int,float)) or not math.isfinite(p[key]) or p[key]!=int(p[key]) for key in ('input field','output field')):raise ValueError('Invalid scalar remap attribute ID')
            if not ((p['input field'] in (1,7,8) and p['output field']==7) or (p['input field'] in (1,3,8) and p['output field']==3) or (p['input field'] in (1,3,8,10) and p['output field']==10 and enabled(definition,'renderers')[0]['function']=='render_sprite_trail') or (p['input field']==8 and p['output field']==5)):raise ValueError('Unsupported scalar remap field')
            from particle_scalar_remap import remap
            remap(p,0.,0.)
        if module['function']=='Radius Scale':
            bias=float(p.get('scale_bias',.5))
            if not math.isfinite(bias) or not 0<=bias<=1:raise ValueError('Invalid particle radius bias')
        if module['function'] in ('Alpha Fade In Simple','Alpha Fade Out Simple'):
            simple_fade(module['function'],p,0.)
        if module['function']=='Alpha Fade Out Random' and (float(p.get('fade out time exponent',1))!=1 or float(p.get('fade bias',.5))!=.5):raise ValueError('Biased random alpha fade-out is unsupported')
        if module['function']=='Ramp Scalar Linear Random':
            from particle_scalar_ramp import validate_supported
            config_ramp=validate_supported(p)
            if config_ramp['field']==4 and renderers[0]['function']!='render_animated_sprites':raise ValueError('Roll ramps require sprite geometry')
        if module['function']=='Oscillate Scalar':
            from particle_scalar_oscillation import settings as full_oscillation_settings
            oscillator=full_oscillation_settings(p,allow_random=True)
            if renderers[0]['function']!='render_animated_sprites':
                if renderers[0]['function']!='render_sprite_trail' or oscillator['oscillation field'] not in (3,7):
                    raise ValueError('Full scalar roll oscillation requires sprite geometry; trail opacity and CPU trail width are supported')
                if oscillator['oscillation field']==3 and material is not None and str(material.get('sfm_particle_shader','')).casefold()!='unlitgeneric':
                    raise ValueError('Full trail radius oscillation currently requires an UnlitGeneric material; GPU spline geometry remains unverified')
        if module['function']=='Oscillate Scalar Simple':
            if int(p.get('oscillation field',7)) not in (3,7,10,16):raise ValueError('Unsupported simple oscillation field')
            if p.get('oscillation field',7)==16:
                from particle_secondary_alpha import settings as secondary_settings
                secondary_settings(p)
            if not all(math.isfinite(float(p.get(key,default))) for key,default in (('oscillation multiplier',2),('oscillation frequency',1),('oscillation rate',0),('oscillation start phase',.5))):raise ValueError('Invalid simple oscillation parameters')
        if any(float(p.get(key,0))!=0 for key in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')):
            if experimental_decay and module['function']=='Lifespan Decay':
                from particle_decay_experimental import activation
                activation(p)
                continue
            if module['function']=='Color Fade':
                from particle_color_timing import settings as color_timing_settings
                color_timing_settings(p)
                continue
            if module['function']!='Rotation Spin Roll':
                authored={key:p[key] for key in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate') if float(p.get(key,0))!=0}
                raise ValueError(f"Operator strength timing is unsupported for {module['function']}: {authored}")
            from particle_emitter_fade import settings as fade_settings
            fade_settings(p)
        if module['function']=='Movement Lock to Control Point':
            from particle_control import lock_settings
            try:lock_settings(p)
            except ValueError:
                if not experimental_partial_lock:raise
                from particle_partial_lock import validate
                validate(p)
                if renderers[0]['function']!='render_animated_sprites':raise ValueError('Experimental fade lock currently requires sprite geometry')
        if module['function']=='Rotation Spin Roll':
            from particle_spin import settings as spin_settings
            spin_settings(p)
    if enabled(definition,'forces'):
        parameters(definition,'operators','Movement Basic')
    for module in enabled(definition,'forces'):
        if module['function']=='twist around axis':
            from particle_twist_axis import settings as twist_settings
            twist_settings(module['parameters'])
        if module['function']=='Force based on distance from plane':
            from particle_plane_force import settings as plane_force_settings
            plane_force_settings(module['parameters'])
            if len(enabled(definition,'forces'))!=1 or any(m['function']=='Movement Lock to Control Point' for m in enabled(definition,'operators')):
                raise ValueError('Combined plane-distance force and other forces or movement lock is unverified')
            p=module['parameters']
            if any(float(p.get(key,0))!=0 for key in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')) or any(float(p.get(key,1))!=1 for key in ('operator time scale min','operator time scale max','operator strength random scale min','operator strength random scale max')):
                raise ValueError('Plane-distance force shared timing/strength is unverified')
        p=module['parameters'];bounds=[p.get('min force',[0,0,0]),p.get('max force',[0,0,0])]
        if any(len(v)!=3 or not all(math.isfinite(float(c)) for c in v) for v in bounds):raise ValueError('Invalid random force vector')
        if any(float(p.get(key,0))!=0 for key in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout','operator fade oscillate')):raise ValueError('Random force strength timing is unsupported')
    omitted=[label+'.'+key for label,p,keys in (('Lifetime Random',life,('lifetime_min','lifetime_max')),('Radius Random',radius,('radius_min','radius_max'))) for key in keys if key not in p]
    if omitted:raise ValueError('Unverified Source default for omitted particle parameter: '+', '.join(omitted))
    life_range=sorted(float(life.get(key,0)) for key in ('lifetime_min','lifetime_max'))
    sequence_life=next((m['parameters'] for m in enabled(definition,'initializers') if m['function']=='lifetime from sequence'),None)
    sequence_modules=[m for m in enabled(definition,'initializers') if m['function']=='Sequence Random']
    if len(sequence_modules)>1 and (sequence_life is not None or any(
            m['function']=='Remap Initial Scalar' and int(m['parameters'].get('input field',8))==9
            for m in enabled(definition,'initializers'))):
        raise ValueError('Repeated Sequence Random with sequence readers requires ordered sequence history')
    if sequence_life is not None and sheet:
        from particle_sheet import sequence_lifetime,validate_sequence_lifetime_order
        initializers=enabled(definition,'initializers');names=[m['function'] for m in initializers]
        validate_sequence_lifetime_order(names)
        sequences=[m['parameters'] for m in initializers if m['function']=='Sequence Random']
        if not sequences:low=high=int(definition['parameters'].get('sequence_number',0))
        else:
            low=min(int(sequence.get('sequence_min',0)) for sequence in sequences)
            high=max(int(sequence.get('sequence_max',0)) for sequence in sequences)
        if not 0<=low<=high<64:raise ValueError('Invalid sequence lifetime range')
        lifetimes=[sequence_lifetime(sheet or {},i,sequence_life) for i in range(low,high+1)]
        life_range=[min(lifetimes),max(lifetimes)]
    radius_range=[float(radius.get(key,-1)) for key in ('radius_min','radius_max')]
    # Installed Radius Random interpolates authored endpoints directly, even
    # descending ranges. Both endpoints must remain nonnegative for sprites.
    if not all(math.isfinite(v) for v in life_range+radius_range) or life_range[0]<0 or life_range[1]<=0 or life_range[1]<life_range[0] or (min(radius_range)<0 and not experimental_ring):
        raise ValueError('Requires explicit valid lifetime and radius ranges')
    if position.get('Control Point Increment Amount',0)!=0:raise ValueError('Incrementing control points not yet supported')
    from particle_emitters import validate as validate_emitters
    validate_emitters(emitters,allow_burst_scaling=allow_burst_scaling)
    renderer=renderers[0]['parameters']
    if renderers[0]['function']=='render_rope':
        from particle_rope import settings as rope_settings
        renderer=rope_settings(renderer)
    from particle_orientation import validate as validate_orientation,control_point as orientation_cp
    from particle_spritecard_geometry import settings as spritecard_settings
    spritecard=spritecard_settings(material or {},renderers[0]['function'])
    if spritecard is not None:
        renderer={**renderer,'orientation_type':spritecard['orientation'],'orientation control point':-1}
    orientation=validate_orientation(renderer,renderers[0]['function'])
    from particle_dual_sequence import settings as dual_settings
    dual=dual_settings(material or {},renderer,renderers[0]['function'])
    if any(m['function']=='Sequence Two Random' for m in enabled(definition,'initializers')) and dual is None:
        raise ValueError('Secondary sequence initialization requires a supported dual-sequence material')
    yaw_modules=enabled(definition,'initializers')
    yaw_modules=[m for m in yaw_modules if m['function']=='Rotation Yaw Random']
    if len(yaw_modules)>1:raise ValueError('Repeated Rotation Yaw Random initializers are unsupported')
    yaw_config=None
    if yaw_modules:
        from particle_orientation import world_plane_yaw
        yaw_config=world_plane_yaw(yaw_modules[0],orientation,renderers[0]['function'],orientation_cp(renderer),spritecard=spritecard is not None)
    yaw_ramps=[m for m in enabled(definition,'operators') if m['function']=='Ramp Scalar Linear Random' and m['parameters'].get('ramp field',3)==12]
    if yaw_ramps:
        if renderers[0]['function']!='render_animated_sprites' or (spritecard is None and orientation==0):
            raise ValueError('Yaw ramps require verified animated-sprite yaw geometry')
        yaw_config=yaw_config or {'ramp_field':12}
    if float(renderer.get('second sequence animation rate',0))!=0 and dual is None:raise ValueError('Dual-sequence particle blending is unsupported')
    return {'rate':sum(float(m['parameters'].get('emission_rate',100)) for m in emitters if m['function']=='emit_continuously'),'emitter':emitter_function,'renderer':renderers[0]['function'],'lifetime':life_range[0],
            'radius':float(radius['radius_min']),'lifetime_range':life_range,'radius_range':radius_range,'orientation':orientation,
            'orientation_control_point':orientation_cp(renderer) if orientation==2 else -1,
            'yaw_attribute':yaw_config,'spritecard_geometry':spritecard,'dual_sequence':dual,
            'cpu_trail_geometry':renderers[0]['function']=='render_sprite_trail' and str((material or {}).get('sfm_particle_shader','')).casefold()=='unlitgeneric',
            'lifetime_exponent':float(life.get('lifetime_random_exponent',1)),'radius_exponent':float(radius.get('radius_random_exponent',1)),
            'ordered_lifetime_samples':lifetime_samples if len(lifetime_samples)>1 else None,
            'definition_lifetime':definition_lifetime if not lifetime_modules else None,
            'sequential_path':path_control,'initial_particles':initial_count,'experimental_ring':ring,
            'control_point':int(ring['control point number']) if ring else path_control['start'] if path_control else int(position.get('Starting Control Point',position.get('control_point_number',0)))}

def birth_ranges(config,rng):
    from particle_distribution import birth_ranges as sample_ranges
    return sample_ranges(config,rng)

def birth_fades(definition,rng):
    """Sample fade durations once at birth, preserving constant cases."""
    result={}
    for index,operator in enumerate(enabled(definition,'operators')):
        if operator['function'] not in ('Alpha Fade In Random','Alpha Fade Out Random'):continue
        word='in' if operator['function']=='Alpha Fade In Random' else 'out'
        p=operator['parameters'];a=float(p.get(f'fade {word} time min',.25));b=float(p.get(f'fade {word} time max',.25))
        if not math.isfinite(a) or not math.isfinite(b) or min(a,b)<0:
            raise ValueError('Invalid alpha fade duration range')
        # Preserve endpoint order: uniform interpolation also supports authored
        # descending ranges. Exact Source particle random streams are unverified.
        result[index]=a if a==b else rng.uniform(a,b)
    return result


def simple_fade(function,parameters,fraction):
    word='in' if function=='Alpha Fade In Simple' else 'out'
    key='proportional fade '+word+' time'
    # Installed pet.dll metadata builders 0x1023c620/0x1023cc90
    # declare .25 and field 7 (the source spells its key "aplha field").
    field=parameters.get('aplha field',7)
    if isinstance(field,bool) or field!=7:raise ValueError('Unsupported simple alpha fade field')
    duration=float(parameters.get(key,.25))
    if not math.isfinite(duration) or not 0<=duration<=1:raise ValueError('Invalid simple alpha fade duration')
    amount=fraction if word=='in' else 1-fraction
    # Operations 0x10271060/0x102711a0 use cubic smoothstep, not a
    # linear ramp. Reciprocal SIMD precision remains approximate here.
    value=min(1.,max(0.,amount/duration)) if duration>0 else (1. if word=='in' else float(amount>0))
    return value*value*(3.-2.*value)

def simple_fade_value(function,parameters,fraction,current,initial):
    """Source simple fades read initial alpha; fade-out only reduces current."""
    curve=simple_fade(function,parameters,fraction)
    word='in' if function=='Alpha Fade In Simple' else 'out'
    duration=float(parameters.get('proportional fade '+word+' time',.25))
    if word=='in':
        return initial*curve if min(1.,max(0.,fraction))<duration else current
    return min(current,initial*curve) if fraction>1.-duration else current

def appearance(definition,age,lifetime,radius,fade_durations=None,allow_signed_radius=False,creation_time=None,oscillation_samples=None):
    alpha=1.;fraction=age/lifetime
    if oscillation_samples:
        definition={**definition,'modules':{**definition['modules'],'operators':[
            {**m,'parameters':oscillation_samples.get(i,m['parameters'])} for i,m in enumerate(definition['modules']['operators'])]}}
    modules=enabled(definition,'operators')
    radius_remap=any(m['function']=='Remap Scalar' and m['parameters']['output field']==3 for m in modules)
    radius_history=radius_remap or any(m['function']=='Ramp Scalar Linear Random' and m['parameters'].get('ramp field',3)==3 for m in modules) or any(m['function']=='Radius Scale' for m in modules)
    full_radius_oscillation=any(m['function']=='Oscillate Scalar' and m['parameters'].get('oscillation field',7)==3 for m in modules)
    radius_ramp=any(m['function']=='Ramp Scalar Linear Random' and m['parameters'].get('ramp field',3)==3 for m in modules)
    if radius_remap or full_radius_oscillation or radius_ramp:
        if creation_time is None:raise ValueError('Radius remap requires particle creation time')
        from particle_radius_remap import radius as remapped_radius
        # A full scalar radius oscillator can legitimately cross zero. Source
        # sprite renderers consume the signed value (which also flips the
        # billboard by 180 degrees); rejecting it discards otherwise valid
        # effects such as the MvM gold fireworks. Keep the sign through mesh
        # generation rather than treating an oscillation trough as a failure.
        radius=remapped_radius(modules,age,lifetime,radius,creation_time,
                               allow_signed=allow_signed_radius or full_radius_oscillation)
    elif radius_history:
        from particle_radius_scale import sampled_radius,mixed_radius
        has_radius_oscillation=any(m['function']=='Oscillate Scalar Simple' and int(m['parameters'].get('oscillation field',7))==3 for m in modules)
        if allow_signed_radius:
            radius=sampled_radius(modules,age,lifetime,radius,allow_signed_radius=True)
        else:radius=(mixed_radius if has_radius_oscillation else sampled_radius)(modules,age,lifetime,radius)
    for index,operator in enumerate(enabled(definition,'operators')):
        p=operator['parameters']
        if operator['function'] in ('Alpha Fade In Simple','Alpha Fade Out Simple'):
            alpha=simple_fade_value(operator['function'],p,fraction,alpha,1.)
        elif operator['function']=='Radius Scale':
            if radius_history:continue
            a=float(p.get('start_time',0));b=float(p.get('end_time',1))
            f=min(1,max(0,(fraction-a)/(b-a))) if b!=a else float(fraction>=b)
            from particle_radius_bias import interpolate
            f=interpolate(f,p.get('scale_bias',.5),p.get('ease_in_and_out',False))
            radius*=float(p.get('radius_start_scale',1))*(1-f)+float(p.get('radius_end_scale',1))*f
        elif operator['function']=='Alpha Fade In Random':
            a=float(p.get('fade in time min',.25));b=float(p.get('fade in time max',.25))
            if fade_durations is not None:a=float(fade_durations[index])
            elif abs(a-b)>1e-7:raise ValueError('Random alpha fade requires a sampled birth duration')
            elapsed=fraction if p.get('proportional 0/1',True) else age
            alpha*=min(1,max(0,elapsed/a)) if a>0 else 1.
        elif operator['function']=='Alpha Fade Out Random':
            a=float(p.get('fade out time min',.25));b=float(p.get('fade out time max',.25))
            if fade_durations is not None:a=float(fade_durations[index])
            elif abs(a-b)>1e-7:raise ValueError('Random alpha fade-out requires a sampled birth duration')
            remaining=1-fraction if p.get('proportional 0/1',True) else lifetime-age
            fade=min(1,max(0,remaining/a)) if a>0 else float(remaining>0)
            if p.get('ease in and out',False):fade=fade*fade*(3-2*fade)
            alpha*=fade
        elif operator['function']=='Oscillate Scalar Simple':
            # Integrate sinusoidal attribute velocity from birth. Explicitly an
            # approximation: Source tick integration/order is not reproduced.
            from particle_oscillation import delta as oscillation_delta
            delta=oscillation_delta(p,age)
            if int(p.get('oscillation field',7))==3 and not radius_history:radius=max(0.,radius+delta)
            elif int(p.get('oscillation field',7))==7:alpha=min(1.,max(0.,alpha+delta))
    return radius,alpha

def _bake(system,descriptor,shot,scene,frames,seconds,fps,materials,curves_factory,scale=.0254,progress=None,experimental_decay=False,experimental_pull=False,experimental_spline=False,experimental_partial_lock=False,collision_trace=None,tint_provider=None,model_factory=None,simulation_contexts=None,retain_leaf_contexts=True,development_pull_lock=False,development_noise=False,particle_frame_step=1):
    import bpy
    from mathutils import Vector
    parent_segments=shot_segments(shot,system,shot.start,shot.start+shot.duration)
    # Overlapping transparent sprites must not terminate paths after 8 layers.
    scene.cycles.transparent_max_bounces=max(scene.cycles.transparent_max_bounces,128)
    control_objects={o.get('sfm_transform_id'):o for o in scene.objects if o.get('sfm_transform_id')}
    base_control_objects=control_objects
    collection=bpy.data.collections.new(system.name+' baked sprites')
    records=[];original_frame=scene.frame_current;depth_ranks={}
    last_scene_time=None
    def set_time(time):
        nonlocal last_scene_time
        frame=1+(time-shot.start)*fps
        whole_frame=math.floor(frame)
        subframe=frame-whole_frame
        scene_time=(whole_frame,subframe)
        # Collision and history queries often ask for the current sample time
        # once per live particle. Re-evaluating the full Blender dependency
        # graph for an unchanged time is redundant; retain the exact pair so
        # fractional-frame animation is still sampled without quantization.
        if (scene_time==last_scene_time and scene.frame_current==whole_frame
                and abs(scene.frame_subframe-subframe)<1e-7):
            return
        scene.frame_set(whole_frame,subframe=subframe)
        last_scene_time=scene_time
    from particle_sampling import samples as sample_particle_frames
    particle_frames,particle_seconds,particle_next_frames=sample_particle_frames(frames,seconds,particle_frame_step)
    particle_frame_step=int(particle_frame_step)
    # Child effects share this system's CP indices. Key by resolved shot time
    # so differing child clocks cannot reuse a position from another time.
    from particle_renderers import passes
    definitions=descriptor['definitions']
    if simulation_contexts is not None:
        from particle_parent_graph import ordered
        definitions=ordered(definitions)
    from particle_parent_retention import required,retain
    required_parent_ids=required(definitions)
    root_descriptor=descriptor;cp_environments={}
    for definition in [p for d in definitions for p in passes(d)]:
        descriptor={**root_descriptor,'control_points':list(root_descriptor.get('control_points',[]))}
        inherited_controls=base_control_objects
        inherited_environment=cp_environments.get(definition.get('parent_instance_id')) if simulation_contexts is not None else None
        if inherited_environment is not None and not isinstance(inherited_environment,Exception):
            points,inherited_controls=inherited_environment
            descriptor['control_points']=list(points)
        cp_environments[definition.get('instance_id')]=(inherited_environment
            if isinstance(inherited_environment,Exception) else (descriptor['control_points'],inherited_controls))
        from particle_names import normalize
        definition=normalize(definition)
        from particle_containers import no_birth_source
        if no_birth_source(definition):
            records.append({'effect':definition['name'],'instance_id':definition.get('instance_id'),
                'parent_instance_id':definition.get('parent_instance_id'),'rendered':True,
                'approximate':False,'geometry_generated':False,'no_visual_expected':True,
                'empty_geometry_reason':'Root particle definition has no emitter, initial particles, parent-particle initializer, or child links; no particle births are expected.'})
            continue
        if not enabled(definition,'renderers'):
            from particle_containers import empty_container
            if empty_container(definition,required_parent_ids):continue
        simulation_only=simulation_contexts is not None and not enabled(definition,'renderers')
        if not enabled(definition,'renderers') and not simulation_only:
            from particle_containers import controller_reason
            reason=controller_reason(definition)
            if reason:
                records.append({'effect':definition['name'],'instance_id':definition.get('instance_id'),
                    'parent_instance_id':definition.get('parent_instance_id'),
                    'rendered':False,'reason':reason,'failure_category':'unsupported_parent_controller'})
                if progress:progress(system.name+' / '+definition['name']+': particle skipped: '+reason)
            continue
        if simulation_only:
            # The current planner validates simulation and renderer together.
            # Supply its inert planning shape; no material or geometry is made.
            definition={**definition,'modules':{**definition['modules'],
                'renderers':[{'function':'render_animated_sprites','parameters':{}}]}}
        if progress:progress(system.name+': baking particle effect '+definition['name'])
        record={'effect':definition['name'],'instance_id':definition.get('instance_id'),
            'parent_instance_id':definition.get('parent_instance_id'),
            'rendered':False,'material_path':definition['parameters'].get('material','').replace('\\','/')}
        if particle_frame_step>1:
            record['particle_frame_sampling']={'step':particle_frame_step,'sampled_frames':len(particle_frames),
                'timeline_frames':len(frames),'held_between_samples':True}
        if definition.get('renderer_pass_count',1)>1:
            record.update(renderer_pass_index=definition['renderer_pass_index'],renderer_pass_count=definition['renderer_pass_count'],renderer_function=enabled(definition,'renderers')[0]['function'])
        try:
            if isinstance(inherited_environment,Exception):raise ValueError(str(inherited_environment))
            if definition.get('end_cap_effect',False):raise ValueError('End-cap particle activation is not yet implemented')
            child_cp_config=None
            from particle_child_cp import FUNCTION as child_cp_function,settings as child_cp_settings
            child_cp_modules=[m for m in enabled(definition,'operators') if m['function']==child_cp_function]
            if child_cp_modules and simulation_contexts is not None:
                cp_environments[definition.get('instance_id')]=ValueError('Parent child-control-point simulation failed or is unavailable')
                if len(child_cp_modules)!=1:raise ValueError('Repeated child-control-point writers require ordered integration')
                child_cp_config=child_cp_settings(child_cp_modules[0]['parameters'])
                definition={**definition,'modules':{**definition['modules'],
                    'operators':[m for m in definition['modules']['operators'] if m['function']!=child_cp_function]}}
                record['experimental_child_control_points']=child_cp_config
                record['child_control_point_limitations']=['Position only; approximate 120 Hz history and birth-ordered active buffer. Source compaction, tick ordering and visual parity are unverified. Repeated-birth feedback and CP-dependent source motion remain rejected.']
            from particle_cp_positions import overlay as cp_position_overlay
            control_objects,cp_position_config=cp_position_overlay(definition,descriptor,inherited_controls,scale,scene)
            if child_cp_config is None:
                cp_environments[definition.get('instance_id')]=(descriptor['control_points'],control_objects)
            # Cached force targets are only reusable within this definition;
            # CP position overrides can give siblings different virtual transforms.
            pull_target_cache={}
            if cp_position_config:
                record['control_point_position_overrides']=[dict(point,location_source_units=list(point['location'])) for point in cp_position_config['points']]
                record['control_point_position_limitations']=cp_position_config['limitations']
            from particle_vector_oscillation import resolve_zero_rate
            definition,zero_vector=resolve_zero_rate(definition)
            if zero_vector:
                record['zero_vector_oscillation']='Installed default zero-rate position oscillation has no contribution'
            model_context=None
            if descriptor.get('control_models') and model_factory is not None:
                definition,model_context=model_factory(definition,descriptor)
            from particle_model_fallback import resolve as resolve_model_fallback
            definition,model_fallback=resolve_model_fallback(definition,descriptor)
            if model_fallback:
                record['model_position_fallback']='No attached control model: emit at control point, matching installed SFM query fallback'
            if model_context is not None:
                record['animated_model_hitboxes']=True
                if any(m['function']=='Position Modify Offset Random' for m in enabled(definition,'initializers')):
                    record.setdefault('limitations',[]).append('Model spawn offsets shift current and previous positions together before model-follow history. Configured-range sampling, Source RNG alignment and exact initializer ordering remain approximate.')
                if model_context.settings.get('motion'):
                    record['ordered_model_motion_operators']=[m['function'] for m in model_context.settings['motion']]
                    record['ordered_model_bone_motion']=any(m['function']=='Movement Lock to Bone' for m in model_context.settings['motion'])
                    record['model_bone_motion_limitations']=['Approximate 120 Hz birth-relative clock; Source startup bypass, tick phase and visual parity remain unverified']
                if model_context.settings.get('sfm_query_ignored_settings'):
                    record['sfm_model_query_ignored_settings']=model_context.settings['sfm_query_ignored_settings']
                    record['sfm_model_query_policy']='Installed SFM query ignores direction bias; requested model surface tracing only warns and does not alter selection'
                record['model_hitbox_limitations']=['Approximate 120 Hz birth-relative history and converter RNG; Source timing, random stream and visual parity unverified']
            from particle_model_fallback import resolve_lerp
            definition,no_hitbox_lerp=resolve_lerp(definition,descriptor)
            if no_hitbox_lerp:
                record['hitbox_movement_fallback']='No attached control model: zero hitbox count skips movement, matching installed SFM operator'
            segments=delayed_segments(parent_segments,float(definition.get('child_delay',0)))
            path=definition['parameters'].get('material','').replace('\\','/')
            if not simulation_only and path not in materials:
                failure=next((m for m in descriptor.get('materials',[]) if m.get('path')==path and m.get('converted') is False),{})
                record.update(reason=failure.get('reason','Particle material unavailable: '+path),failure_category=failure.get('failure_category','material_unavailable'),material_path=path)
                if progress:progress(system.name+' / '+definition['name']+': particle skipped: '+record['reason'])
                records.append(record);continue
            maintained=any(module['function']=='emit to maintain count' for module in enabled(definition,'emitters'))
            cull_modules=[m for m in enabled(definition,'operators') if m['function']=='Cull when crossing plane']
            if cull_modules and maintained:raise ValueError('Plane culling with maintained emission requires ordered birth feedback')
            has_tint=any(m['function']=='Color Random' and float(m['parameters'].get('tint_perc',0))!=0 for m in enabled(definition,'initializers'))
            if has_tint and tint_provider is not None and maintained:
                raise ValueError('Tint provider for maintained particle lifecycle is unverified')
            use_shared_maintained=False
            from particle_maintained_route import native_velocity_noise
            if maintained and not native_velocity_noise(definition):
                try:
                    plan(definition,{} if simulation_only else json.loads(materials[path].get('sfm_particle_sheet','{}')))
                    use_shared_maintained=True
                except ValueError:
                    pass
            if maintained and not use_shared_maintained:
                from maintained_sprites import bake as bake_maintained
                path=definition['parameters']['material'].replace('\\','/')
                maintained_record=bake_maintained(system,definition,descriptor,shot,scene,frames,seconds,materials[path],curves_factory,scale)
                maintained_record['material_path']=path
                maintained_record['instance_id']=definition.get('instance_id')
                maintained_record['parent_instance_id']=definition.get('parent_instance_id')
                if native_velocity_noise(definition):
                    maintained_record.setdefault('limitations',[]).append('Velocity Noise uses the maintained-count lifecycle path even when experimental ordered noise is enabled; replacement-slot sampling and motion remain approximate.')
                records.append(maintained_record)
                continue
            material={} if simulation_only else materials[path]
            if material.get('sfm_particle_texture_recovery'):record['texture_recovery']=json.loads(material['sfm_particle_texture_recovery'])
            sheet=json.loads(material.get('sfm_particle_sheet','{}'))
            pull_modules=[m for m in enabled(definition,'forces') if m['function'].casefold()=='pull towards control point']
            planned_definition=definition
            if pull_modules and not experimental_pull and any(m['function']=='Oscillate Vector' and m['parameters'].get('oscillation field',0)==0
                                    for m in enabled(definition,'operators')):
                raise ValueError('Pull force with position oscillation requires ordered pull history')
            ordered_spatial=any(m['function']=='Oscillate Vector' and m['parameters'].get('oscillation field',0)==0
                                for m in enabled(definition,'operators'))
            if experimental_pull and pull_modules:
                from particle_spatial_force_context import ordered_movement_supported
                if ordered_movement_supported(definition):
                    ordered_spatial=True
            twist_modules=[m for m in enabled(definition,'forces') if m['function']=='twist around axis']
            if twist_modules:
                from particle_spatial_force_context import ordered_movement_supported
                has_translation_lock=any(m['function']=='Movement Lock to Control Point' for m in enabled(definition,'operators'))
                locked_twist_path=bool(development_pull_lock and has_translation_lock)
                if ordered_movement_supported(definition,allow_translation_lock=locked_twist_path):ordered_spatial=True
                if not ordered_spatial and (not experimental_pull or not pull_modules):raise ValueError('Twist force requires ordered vector history or the experimental pull path')
                from particle_twist_axis import settings as twist_settings
                for module in twist_modules:
                    index=twist_settings(module['parameters'])['control_point']
                    if index>=len(descriptor['control_points']) or descriptor['control_points'][index]['id'] not in control_objects:
                        raise ValueError(f'Twist force requires imported control point {index}')
                record['twist_limitations']=['World axis only; approximate 120 Hz history. Source float rounding and tick parity are unverified.']
            if experimental_pull and pull_modules:
                from particle_pull_settings import settings as pull_settings
                if len(pull_modules)!=1:raise ValueError('Experimental pull requires one pull force')
                parsed_pull=pull_settings(pull_modules[0]['parameters'])
                if parsed_pull['prototype_unsupported_features']:raise ValueError('; '.join(parsed_pull['prototype_unsupported_features']))
                pull_cp=parsed_pull['control_point']
                if pull_cp>=len(descriptor['control_points']):raise ValueError(f'Pull force requires missing control point {pull_cp}')
                pull_id=descriptor['control_points'][pull_cp]['id']
                if pull_id not in control_objects:raise ValueError(f'Pull control point {pull_cp} has no imported transform')
                if any(m['function']=='Movement Lock to Control Point' for m in enabled(definition,'operators')) and not development_pull_lock:raise ValueError('Combined pull and movement lock is unverified')
                planned_definition={**definition,'modules':{**definition['modules'],'forces':[m for m in definition['modules']['forces'] if m['function'].casefold()!='pull towards control point']}}
            pull_lock_active=bool(development_pull_lock and ((experimental_pull and pull_modules) or (ordered_spatial and twist_modules))
                and any(m['function']=='Movement Lock to Control Point' for m in enabled(definition,'operators')))
            if pull_lock_active:
                planned_definition={**planned_definition,'modules':{**planned_definition['modules'],
                    'operators':[m for m in planned_definition['modules']['operators'] if m['function']!='Movement Lock to Control Point']}}
                record['development_pull_lock']=True
                record['pull_lock_limitations']=['Development translation-only chronological history; Source timing, RNG and visual parity unverified']
            from particle_renderers import spline_ring_enabled
            collision_modules=[m for m in enabled(definition,'constraints') if m['function']=='Collision via traces']
            collision_config=None;collision_histories={}
            secondary_histories={}
            secondary_operators=[m['parameters'] for m in enabled(definition,'operators') if m['function']=='Oscillate Scalar Simple' and m['parameters'].get('oscillation field',7)==16]
            if collision_modules and collision_trace is not None:
                if len(collision_modules)!=1:raise ValueError('Repeated trace collision constraints are unverified')
                if any(m['function']=='Movement Lock to Control Point' for m in enabled(definition,'operators')):
                    raise ValueError('Trace collision with movement lock is unverified')
                if any(m['function']!='Collision via traces' for m in enabled(definition,'constraints')):
                    raise ValueError('Combined trace and other constraints are unverified')
                from particle_collision_settings import settings as collision_settings
                collision_config=collision_settings(collision_modules[0]['parameters'])
                planned_definition={**planned_definition,'modules':{**planned_definition['modules'],
                    'constraints':[m for m in planned_definition['modules']['constraints'] if m['function']!='Collision via traces']}}
                collision_scene=descriptor.get('collision_scene',{})
                record['development_trace_collision']=not collision_scene.get('production_enabled',False)
                record['world_brush_trace_collision']=bool(collision_scene.get('production_enabled',False))
                record['collision_limitations']=['World brushes only; model and displacement collisions are not implemented',
                    '120 Hz swept radius hull; Source trace caching, boundary epsilon, RNG and tick ordering differ']
            ring_enabled=spline_ring_enabled(planned_definition,material,experimental_spline)
            parent_initializer=None;parent_context=None
            parent_modules=[m for m in enabled(definition,'initializers') if m['function']=='Position From Parent Particles']
            if parent_modules and simulation_contexts is not None:
                if len(parent_modules)!=1:raise ValueError('Repeated parent position initializers require ordered integration')
                if model_context is not None:
                    raise ValueError('Combined parent-particle and model-hitbox spawning requires ordered integration')
                parent_context=simulation_contexts.get(definition.get('parent_instance_id'))
                if parent_context is None:raise ValueError('Parent simulation context is missing or unsupported')
                from particle_parent_initializer import Initializer
                parent_initializer=Initializer(parent_modules[0]['parameters'])
                planned_definition={**planned_definition,'modules':{**planned_definition['modules'],
                    'initializers':[{'function':'Position From Control Points','parameters':{'control_point_number':0}}
                        if m['function']=='Position From Parent Particles' else m for m in planned_definition['modules']['initializers']]}}
                record['development_parent_initialization']=True
                record['parent_initialization_limitations']=['Approximate 120 Hz parent buffer and birth-order active list; Source RNG, death compaction, killed-parent scheduling and initializer ordering remain unverified']
            from particle_parent_attribute import NAME as parent_attribute_name,prepare as prepare_parent_attributes
            parent_attributes=prepare_parent_attributes(definition)
            if parent_attributes:
                if parent_context is None or parent_initializer is None:
                    raise ValueError('Parent attributes require complete parent simulation context')
                planned_definition={**planned_definition,'modules':{**planned_definition['modules'],
                    'initializers':[m for m in planned_definition['modules']['initializers'] if m['function']!=parent_attribute_name]}}
                record['parent_attribute_inheritance']=[dict(field=op.field,scale=op.scale,increment=op.increment,random=op.random) for op in parent_attributes]
                record.setdefault('limitations',[]).append('Parent lifetime/radius are copied at child birth using independent integer cursors and the converter live buffer. Source active-buffer compaction, tick phase, random stream, killed-parent dispatch and visual parity remain unverified.')
            from particle_parent_update import NAME as parent_update_name,prepare as prepare_parent_updates
            parent_updates=prepare_parent_updates(definition)
            if parent_updates:
                if parent_context is None or parent_initializer is None:
                    raise ValueError('Parent update requires complete parent simulation and supported parent births')
                planned_definition={**planned_definition,'modules':{**planned_definition['modules'],
                    'operators':[{**m,'parameters':{**m['parameters'],'operator enabled':False}}
                        if m['function']==parent_update_name else m for m in planned_definition['modules']['operators']]}}
                record['parent_vector_updates']=True
                record.setdefault('limitations',[]).append('Parent position buffers update in authored order on an approximate 120 Hz collection clock. Birth-order active slots, death compaction, Source random stream and engine tick parity remain unverified.')
            noise_birth=bool(development_noise and any(m['function'] in ('Remap Noise to Scalar','Velocity Noise') for m in enabled(definition,'initializers')))
            warp_modules=[m for m in enabled(definition,'initializers') if m['function']=='Position Modify Warp Random']
            if warp_modules and (noise_birth or parent_initializer is not None or model_context is not None):
                raise ValueError('Position warp combined with ordered noise, parent, or model births requires ordered position history')
            if noise_birth:
                if parent_initializer is not None or model_context is not None:
                    raise ValueError('Ordered noise parent/model birth integration is unfinished')
                from particle_noise_bake_adapter import prepare as noise_plan
                config=noise_plan(planned_definition,plan,sheet=sheet,experimental_decay=experimental_decay,experimental_ring=ring_enabled,experimental_partial_lock=experimental_partial_lock,allow_tint=tint_provider is not None,allow_burst_scaling=True,material=material)
                record['development_ordered_noise_birth']=True
                if config['source_velocity_noise_birth']:
                    record['velocity_noise_initialization']='Three-channel installed spatial/time noise; two-pass birth order'
                    record['initializer_execution_indices']=config['initializer_order']
                    record['velocity_noise_limitations']=['Converter RNG, physical-velocity integration, engine emission ticks and Source image parity remain approximate. Control-point/path multi-attribute births, parent/model births, maintained emission and shared strength/timing gates remain unsupported in this path.']
            else:
                config=plan(planned_definition,sheet,experimental_decay=experimental_decay,experimental_ring=ring_enabled,experimental_partial_lock=experimental_partial_lock,allow_tint=tint_provider is not None,allow_burst_scaling=True,material=material)
            cp_vector_modules=[m for m in enabled(definition,'initializers') if m['function']=='Remap Control Point to Vector']
            cp_vector_controls={}
            if cp_vector_modules:
                from particle_cp_vector_color import settings as cp_vector_settings
                for module in cp_vector_modules:
                    index=cp_vector_settings(module['parameters'])['control_point']
                    if index>=len(descriptor['control_points']) or descriptor['control_points'][index]['id'] not in control_objects:
                        raise ValueError(f'RGB vector initializer requires imported control point {index}')
                    cp_vector_controls[index]=control_objects[descriptor['control_points'][index]['id']]
                record['control_point_rgb_initializers']=[cp_vector_settings(m['parameters']) for m in cp_vector_modules]
                record['control_point_rgb_limitations']=['CP component data sampled at approximate birth times; Source emission-batch timing and visual parity are unverified. RGB remaps run after ordinary color initialization in pass two.']
            def cp_vector_query(index):
                control_point=cp_vector_controls[index].evaluated_get(scene.view_layers[0].depsgraph)
                return tuple(float(v)/scale for v in control_point.matrix_world.translation)
            if config.get('definition_lifetime') is not None:
                record['definition_lifetime']=config['definition_lifetime']
            for force in enabled(definition,'forces'):
                if force['function']=='Force based on distance from plane':
                    from particle_plane_force import settings as plane_force_settings
                    index=plane_force_settings(force['parameters'])['Control point number']
                    if index>=len(descriptor['control_points']) or descriptor['control_points'][index]['id'] not in control_objects:
                        raise ValueError(f'Plane-distance force requires imported control point {index}')
                    record['plane_force_limitations']=['120 Hz midpoint integration; Source tick history and floating-point parity are unverified']
            if config.get('ordered_lifetime_samples'):
                record['ordered_lifetime_initializers']=len(config['ordered_lifetime_samples'])
                record['ordered_lifetime_limitations']=['Last authored write wins; earlier samples consumed. Source RNG stream and ordering relative to other randomized initializer types remain approximate.']
            if config.get('experimental_ring'):
                if config['experimental_ring']['even distribution']:
                    record['experimental_ring_initialization']=True
                    record['normal_only_operations_not_evaluated']=True
                    record['normal_operation_scope']='Installed spline shader does not consume normal stream; other renderers remain unsupported'
                else:
                    record['random_ring_initialization']=True
                    record['random_ring_limitations']=['Zero thickness without override control points; random stream, birth counter reset and Source tick phase remain approximate']
            if config['orientation']==1:
                record['orientation']='upright_world_z'
                record['orientation_limitations']=['Geometry traced from installed mode-1 helper; camera interface identity and Source visual parity unverified',
                                                    'Orientation control points and degenerate horizontal camera axes are unsupported']
            if config.get('yaw_attribute'):
                record['yaw_attribute']={'field':12,'units':'radians','separate_from_roll':True}
                record['yaw_limitations']=['Source RNG and floating point rounding are approximate; Source visual parity is unverified']
            if config['orientation']==2:
                record['orientation']='world_xy_plane' if config['orientation_control_point']==-1 else 'control_point_plane'
                record['orientation_control_point']=config['orientation_control_point']
                record['orientation_limitations']=['Source renderer appearance and UV parity unverified']
            if config.get('spritecard_geometry'):
                record['spritecard_geometry']=config['spritecard_geometry']
                record['orientation_limitations']=['Material orientation overrides PCF orientation as in the installed SpriteCard path',
                    'Screen-size fades, shader float32 trig and Source visual parity remain unverified']
            dual_tables={}
            if config.get('dual_sequence'):
                record['dual_sequence']=config['dual_sequence']
                record['dual_sequence_limitations']=['Installed table, UV zoom and basic blend math; Source RNG/ticks, texture filtering, depth/screen fades and image parity remain unverified',
                    'The installed shader reads MAXLUMFRAMEBLEND1 for both frame-blend flags']
                record['limitations']=[s for s in record.get('limitations',[]) if not s.startswith('Texture sheets use stepped frame selection')]
            if experimental_pull and pull_modules:
                record['experimental_pull']=True
                record['pull_limitations']=['Offline midpoint integration; Source simulation ticks, RNG and trajectories are unverified',
                                            'Paused-clock control-point sampling uses the end of the plateau',
                                            'One nonlocal pull force only; shared strength timing and movement lock are rejected']
                if ordered_spatial:
                    record['pull_limitations'][0]='Ordered 120 Hz position-buffer integration; Source simulation ticks, RNG and trajectories are unverified'
                if pull_lock_active:
                    record['pull_limitations'][0]='Development ordered 120 Hz pull and translation-lock history; Source ticks, RNG and trajectories are unverified'
                    record['pull_limitations'][2]='One nonlocal pull force with full translation attachment; rotation, distance fades and shared timing/strength remain rejected'
            from particle_clock_prepared import PreparedInverse
            plane_force_configs=[m['parameters'] for m in enabled(definition,'forces') if m['function']=='Force based on distance from plane']
            prepared_clock=PreparedInverse(segments) if (plane_force_configs or pull_modules or (ordered_spatial and twist_modules)) else None
            plane_histories={}
            cp=descriptor['control_points'][config['control_point']]['id']
            control=control_objects[cp]
            plane_controls=[]
            for module in enabled(definition,'constraints'):
                if module['function']=='Collision via traces' and collision_config is not None:continue
                from particle_plane import settings as plane_settings
                plane=plane_settings(module['parameters']);index=int(plane['control point number'])
                if index>=len(descriptor['control_points']):raise ValueError(f'Plane requires missing control point {index}')
                plane_id=descriptor['control_points'][index]['id']
                if plane_id not in control_objects:raise ValueError(f'Plane control point {index} has no transform')
                plane_controls.append((plane,control_objects[plane_id]))
            if plane_controls:record['plane_constraint_limitations']=['Radius-aware projection at sampled frames; Source per-tick collision/force history is not verified']
            color_light_config=None;light_controls={}
            for module in enabled(definition,'operators'):
                if module['function']!='Color Light from Control Point':continue
                from particle_color_lights import settings as color_light_settings
                color_light_config=color_light_settings(module['parameters'])
                for light in color_light_config['lights']:
                    if not any(light['color']):continue
                    index=light['cp']
                    if index>=len(descriptor['control_points']):raise ValueError(f'Particle light requires missing control point {index}')
                    light_id=descriptor['control_points'][index]['id']
                    if light_id not in control_objects:raise ValueError(f'Particle light control point {index} has no transform')
                    light_controls[index]=control_objects[light_id]
                record['color_light_limitations']=['Static point lights without normal incidence; sampled control-point positions and scalar math approximate Source SSE/tick behavior; installed light 4 descriptor aliases light 3']
            orientation_control=None
            orientation_index=config['orientation_control_point']
            if orientation_index>=0:
                if orientation_index>=len(descriptor['control_points']):raise ValueError(f'Sprite orientation requires missing control point {orientation_index}')
                orientation_id=descriptor['control_points'][orientation_index]['id']
                if orientation_id not in control_objects:raise ValueError(f'Sprite orientation control point {orientation_index} has no imported transform')
                orientation_control=control_objects[orientation_id]
            path_controls=None
            if config['sequential_path']:
                p=config['sequential_path']
                path_controls=(control_objects[descriptor['control_points'][p['start']]['id']],control_objects[descriptor['control_points'][p['end']]['id']])
            path=definition['parameters']['material'].replace('\\','/')
            material={} if simulation_only else materials[path]
            from particle_sheet import coordinates
            sheet=json.loads(material.get('sfm_particle_sheet','{}'))
            renderer=enabled(definition,'renderers')[0]['parameters']
            if config['renderer']=='render_rope':
                from particle_rope import settings as rope_settings
                renderer=rope_settings(renderer)
            maximum=int(definition['parameters'].get('max_particles',1000))
            if maximum<=0 or maximum>100000:raise ValueError('Invalid maximum particle count')
            record['authored_maximum_particles']=maximum
            # Installed collection allocator 0x101e9900 limits active storage to 5000.
            maximum=min(maximum,5000)
            record['effective_maximum_particles']=maximum
            visible_samples=sum(bool(shot.value(system,'visible',float(t),True)) for t in seconds)
            if not visible_samples:
                record.update(rendered=True,approximate=True,geometry_generated=False,
                              frame_meshes=0,total_quads=0,visible_sample_count=0,
                              empty_geometry_reason='System hidden at every sampled time',
                              birth_history_evaluated=False,
                              simulation_validation='Not evaluated because every requested sample is hidden')
                records.append(record)
                continue
            from particle_emitters import births as emitter_births
            maintained_ranges={}
            if use_shared_maintained:
                from particle_maintain_count import schedule
                lifetime_rng=random.Random(str(particle_seed(descriptor,definition))+':maintained lifetimes')
                def maintained_lifetime(birth):
                    maintained_ranges[birth.index]=birth_ranges(config,lifetime_rng)
                    return maintained_ranges[birth.index][0]
                births=schedule(segments,parameters(definition,'emitters','emit to maintain count'),maximum,maintained_lifetime)
                record['maintained_count_limitations']=['Maintained-count refill uses an approximate 120 Hz clock and pre-refill lifetime expiry; Source tick/death ordering and RNG parity remain unverified']
            else:
                burst_scale_samples=[]
                def burst_scale_sample(cp,field,time):
                    if cp>=len(descriptor['control_points']):raise ValueError('Burst scaling control point is missing')
                    control=control_objects.get(descriptor['control_points'][cp]['id'])
                    if control is None:raise ValueError('Burst scaling control point transform is missing')
                    set_time(time)
                    value=float(control.matrix_world.translation[field])/scale
                    burst_scale_samples.append(dict(control_point=cp,component=field,shot_time=float(time),value_source_units=value))
                    return value
                births=emitter_births(enabled(definition,'emitters'),segments,particle_seed(descriptor,definition),seconds,maximum_particles=maximum,burst_scale_sample=burst_scale_sample)
                if any(m['function']=='emit_instantaneously' and int(m['parameters'].get('emission count scale control point',-1))>=0 for m in enabled(definition,'emitters')):
                    record['burst_scale_samples']=burst_scale_samples
                    record.setdefault('limitations',[]).append('Control-point burst scaling samples once at the first emitting start crossing and preserves the initialized count. Continuous clock inversion approximates Source tick phase and previous-call interpolation; snapshot overrides remain unsupported.')
                if any(m['function']=='emit noise' for m in enabled(definition,'emitters')):
                    record['noise_emitter_limitations']=['Installed SFM lookup-table noise with approximate 120 Hz emission scheduling; engine tick phase, random ordering and live Source parity remain unverified']
            from particle_initial import prepend,creation_time
            initial_time=creation_time(parent_segments,float(definition.get('child_delay',0)))
            if config['initial_particles'] and initial_time is not None:
                births=prepend(births,config['initial_particles'],initial_time)
            if child_cp_config is not None:
                from particle_child_cp_blender import validate_source
                validate_source(definition,births)
            # Position initializers capture the control point at birth, not at render.
            from particle_sprite_state import sample,evaluate
            positions={};rotations={};ranges={};fades={};states={};rng=random.Random(particle_seed(descriptor,definition))
            sphere_distribution=None
            sphere_initializer=next((m['parameters'] for m in enabled(definition,'initializers')
                                     if m['function']=='Position Within Sphere Random'
                                     and m['parameters'].get('randomly distribute to highest supplied Control Point',False)),None)
            if sphere_initializer is not None:
                from particle_sphere_distribution import settings as sphere_distribution_settings
                sphere_distribution=sphere_distribution_settings(
                    sphere_initializer,len(descriptor.get('control_points',[]))-1)
                record['control_point_distribution']={**sphere_distribution,
                    'selection':'uniform integer per birth from configured starting CP through highest supplied CP',
                    'source_rng_parity_verified':False,
                    'limitations':['Source selection distribution and RNG stream are approximate.',
                                    'Only zero distribution-growth time and unscaled control points are supported.']}
            lock=None if pull_lock_active else next((m['parameters'] for m in enabled(definition,'operators') if m['function']=='Movement Lock to Control Point'),None)
            locked_control=control_objects[descriptor['control_points'][int(lock.get('control_point_number',0))]['id']] if lock else None
            from particle_birth_capacity import ActiveBirthCapacity
            locked_births={};lock_fades={};active_birth_capacity=ActiveBirthCapacity(maximum);partial_lock=False;lock_positions={};lock_clock=None
            if lock and experimental_partial_lock:
                from particle_control import lock_settings
                try:lock_settings(lock)
                except ValueError:
                    from particle_partial_lock import validate
                    _,lock_threshold=validate(lock);partial_lock=True
                    lock_clock=PreparedInverse(segments)
                    record['experimental_partial_lock']=True
                    record['partial_lock_limitations']=['Fade-lock translation samples approximate 120 Hz simulation-age history; Source tick phase and random stream are unverified']
            def lock_position(time):
                from particle_target_time import cache_key
                # Historical bisection can produce different double timestamps
                # that Blender evaluates at the same float32 subframe. Share
                # only those identical Blender evaluations, without changing
                # sampling times or fade integration.
                key=cache_key(locked_control.name,time,shot.start,fps)
                if key not in lock_positions:
                    set_time(time)
                    lock_positions[key]=tuple(v/scale for v in locked_control.matrix_world.translation)
                return lock_positions[key]
            from particle_birth_sampler import bind as bind_birth_sampler
            evaluate_birth=bind_birth_sampler(
                pull_lock=pull_lock_active, states=states, plane_force_configs=plane_force_configs, experimental_pull=experimental_pull, pull_modules=pull_modules,
                ordered_spatial=ordered_spatial, twist_modules=twist_modules, definition=definition, positions=positions,
                scale=scale, record=record, plane_histories=plane_histories, evaluate=evaluate,
                planned_definition=planned_definition, Vector=Vector, model_context=model_context, shot=shot,
                pull_target_cache=pull_target_cache, segments=segments, scene=scene, prepared_clock=prepared_clock,
                set_time=set_time, control_objects=control_objects, descriptor=descriptor, fps=fps,
            )
            cull_history=None
            if cull_modules:
                from particle_decay_experimental import requires_extended_history
                if (locked_control is not None or pull_lock_active or model_context is not None
                        or plane_controls or collision_config is not None
                        or requires_extended_history(definition['modules']['operators'],experimental_decay)):
                    raise ValueError('Plane culling with locks, models, constraints or delayed decay requires complete ordered motion history')
                operators=enabled(definition,'operators')
                cut=next(i for i,m in enumerate(operators) if m['function']=='Cull when crossing plane')
                for module in operators[cut+1:]:
                    if (module['function'] in ('Movement Basic','Set Control Point Positions')
                            or (module['function']=='Oscillate Vector' and int(module['parameters'].get('oscillation field',0))==0)):
                        raise ValueError('Motion or CP writes after plane culling require ordered operator-stage history')
                from particle_cull_plane import settings as cull_settings
                from particle_cull_history import History as CullHistory
                from particle_birth_capacity import DeathAwareBirthCapacity
                from particle_clock_prepared import PreparedInverse
                cull_config=cull_settings(cull_modules[0]['parameters']);cp=cull_config['control_point']
                if cp>=len(descriptor['control_points']) or descriptor['control_points'][cp]['id'] not in control_objects:
                    raise ValueError('Cull plane requires an imported control point '+str(cp))
                cull_control=control_objects[descriptor['control_points'][cp]['id']]
                cull_clock=PreparedInverse(segments)
                def cull_position(birth,age,life):
                    offset,_,_,_=evaluate_birth(birth,age,life)
                    return tuple((positions[birth.index][i]+offset[i])/scale for i in range(3))
                def cull_control_position(birth,age):
                    when=cull_clock.query(birth.simulation_time+age,side='right',minimum_time=birth.time)
                    previous_frame,previous_subframe=scene.frame_current,scene.frame_subframe
                    try:
                        set_time(when)
                        return tuple(v/scale for v in cull_control.matrix_world.translation)
                    finally:scene.frame_set(previous_frame,subframe=previous_subframe)
                cull_history=CullHistory(cull_position,cull_control_position,normal=cull_config['normal'],offset=cull_config['offset'])
                active_birth_capacity=DeathAwareBirthCapacity(maximum,cull_history)
                record['plane_culling']={**cull_config,'simulation_step':1/120.,'authored_lifetime_preserved':True}
                record.setdefault('limitations',[]).append('Plane culling uses fixed birth-relative 120 Hz samples and pre-admission history; exact Source tick/dispatch phase and SIMD boundary rounding remain unverified.')
            birth_progress_time=wall_clock.monotonic()
            if progress:progress(f'{system.name} / {definition["name"]}: sampling {len(births)} particle births')
            chaotic_parameters=next((m['parameters'] for m in enabled(definition,'initializers') if m['function']=='Position From Chaotic Attractor'),None)
            chaotic_context=(0.,0.,0.)
            from particle_sequence import SequenceSelection
            sequence_contexts={index:SequenceSelection(module['parameters'],rng)
                               for index,module in enumerate(definition['modules']['initializers'])
                               if module['function']=='Sequence Random' and module['parameters'].get('operator enabled',True)}
            sequence_context=sequence_contexts or None
            birth_control_samples_static=False
            if (model_context is None and parent_initializer is None and collision_config is None
                    and tint_provider is None and not descriptor.get('control_models')
                    and descriptor.get('control_points')):
                from particle_static_transform import transform_is_static
                birth_control_samples_static=True
                for point in descriptor['control_points']:
                    obj=control_objects.get(point['id'])
                    if obj is None or not transform_is_static(obj):
                        birth_control_samples_static=False;break
                if birth_control_samples_static:
                    record['static_control_birth_sampling']='Skipped redundant Blender frame evaluation for constant control transforms'
            for birth_number,birth in enumerate(births,1):
                if birth.time>float(seconds[-1]):break
                if progress and birth_number%250==0 and wall_clock.monotonic()-birth_progress_time>=2:
                    progress(f'{system.name} / {definition["name"]}: particle births {birth_number}/{len(births)}')
                    birth_progress_time=wall_clock.monotonic()
                if cull_history is not None:cull_history.advance(math.nextafter(birth.simulation_time,-math.inf))
                if not active_birth_capacity.has_capacity(birth.simulation_time):continue
                if not birth_control_samples_static:set_time(birth.time)
                birth_control=control
                if sphere_distribution is not None and not noise_birth:
                    from particle_sphere_distribution import choose as choose_sphere_control
                    selected_cp=choose_sphere_control(rng,sphere_distribution)
                    selected_id=descriptor['control_points'][selected_cp]['id']
                    birth_control=control_objects.get(selected_id)
                    if birth_control is None:
                        raise ValueError(f'Sphere distribution control point {selected_cp} has no transform')
                positions[birth.index]=birth_control.matrix_world.translation.copy()
                if path_controls:
                    from particle_path import point
                    positions[birth.index]=Vector(point(birth.index,config['sequential_path']['parameters'],path_controls[0].matrix_world.translation,path_controls[1].matrix_world.translation))
                if locked_control:locked_births[birth.index]=(locked_control.matrix_world.translation.copy(),locked_control.matrix_world.to_quaternion())
                if noise_birth and use_shared_maintained:raise ValueError('Noise births in maintained emitters require ordered lifecycle integration')
                ranges[birth.index]=(config['lifetime'],config['radius']) if noise_birth else maintained_ranges[birth.index] if use_shared_maintained else birth_ranges(config,rng)
                life,radius=ranges[birth.index]
                chaotic_birth=None
                if chaotic_parameters is not None:
                    from particle_chaotic_attractor import step as chaotic_step
                    following=chaotic_step(chaotic_context,chaotic_parameters)
                    chaotic_birth=(chaotic_context,following)
                    chaotic_context=following
                if life<=0 and not noise_birth:continue
                offset_rotations={}
                for offset_index,offset_module in enumerate(definition['modules']['initializers']):
                    offset=offset_module['parameters']
                    if offset_module['function']!='Position Modify Offset Random' or not offset.get('operator enabled',True) or not offset.get('offset in local space 0/1',False):continue
                    cp=int(offset.get('control_point_number',0))
                    if cp>=len(descriptor['control_points']):raise ValueError(f'Offset initializer requires missing control point {cp}')
                    offset_control=control_objects.get(descriptor['control_points'][cp]['id'])
                    if offset_control is None:raise ValueError(f'Offset initializer requires imported control point {cp}')
                    offset_rotations[offset_index]=offset_control.matrix_world.to_quaternion()
                offset_rotation=offset_rotations or None
                velocity=next((m['parameters'] for m in enabled(definition,'initializers') if m['function']=='Velocity Random'),None)
                velocity_rotation=None
                if velocity is not None:
                    velocity_control=control_objects[descriptor['control_points'][int(velocity.get('control_point_number',0))]['id']]
                    velocity_rotation=velocity_control.matrix_world.to_quaternion()
                ring_context={'counter':birth.index,'batch_count':1,'rotation':tuple(tuple(row) for row in birth_control.matrix_world.to_quaternion().to_matrix())} if config.get('experimental_ring') else None
                tint_arguments={} if tint_provider is None else {'tint_query':lambda parameters:tint_provider(definition,parameters,birth.time,birth.simulation_time)}
                if noise_birth:
                    from particle_ordered_birth import sample as ordered_birth
                    def query_birth_control(index):
                        if index>=len(descriptor['control_points']):raise ValueError('Missing ordered birth control point')
                        obj=control_objects[descriptor['control_points'][index]['id']]
                        return tuple(obj.matrix_world.translation/scale),obj.matrix_world.to_quaternion()
                    states[birth.index],_=ordered_birth(definition,rng,scale,birth.simulation_time,birth.index,query_birth_control,(0.,0.,0.),sequence_context=sequence_context,highest_control_point=len(descriptor.get('control_points',[]))-1,initializer_order=config.get('initializer_order'),**tint_arguments)
                    positions[birth.index]=states[birth.index].pop('position')
                    life=states[birth.index]['lifetime']
                    if life<=0:
                        del states[birth.index];del ranges[birth.index]
                        continue
                else:
                    states[birth.index]=sample(definition,rng,scale,birth_control.matrix_world.to_quaternion(),birth.simulation_time,radius,life,birth.index,offset_rotation,velocity_rotation,allow_signed_radius=bool(ring_context),ring_context=ring_context,chaotic_birth=chaotic_birth,sequence_context=sequence_context,cp_vector_query=cp_vector_query if cp_vector_modules else None,**tint_arguments)
                    if warp_modules:
                        from particle_warp import apply_birth
                        def warp_control_query(index):
                            if index>=len(descriptor.get('control_points',[])):
                                raise ValueError(f'Warp initializer requires imported control point {index}')
                            obj=control_objects.get(descriptor['control_points'][index]['id'])
                            if obj is None:raise ValueError(f'Warp initializer requires imported control point {index}')
                            matrix=obj.matrix_world.to_quaternion().to_matrix()
                            rotation=tuple(tuple(float(matrix[row][column]) for column in range(3)) for row in range(3))
                            return tuple(float(v)/scale for v in obj.matrix_world.translation),rotation
                        warped_position,warped_offset,warped_velocity=apply_birth(
                            tuple(float(v)/scale for v in positions[birth.index]),
                            tuple(float(v)/scale for v in states[birth.index]['offset']),
                            tuple(float(v)/scale for v in states[birth.index]['velocity']),
                            enabled(definition,'initializers'),birth.simulation_time,warp_control_query,rng)
                        positions[birth.index]=Vector(warped_position)*scale
                        states[birth.index]['offset']=Vector(warped_offset)*scale
                        states[birth.index]['velocity']=Vector(warped_velocity)*scale
                        record.setdefault('limitations',[]).append('Position Modify Warp Random scales birth position, spawn offset and velocity in the selected control-point frame; timing and Source random-stream parity are approximate.')
                if parent_initializer is not None:
                    from particle_sim import simulation_at
                    from particle_parent_initializer import motion as inherited_motion
                    parent_clock=simulation_at(parent_context.segments,birth.time)
                    tick=1/120.
                    inherited=parent_initializer.initialize(parent_context.snapshot(parent_clock,tick),parent_clock,tick,
                        rng.random() if parent_initializer.random else None)
                    if inherited is None:
                        del states[birth.index];del ranges[birth.index]
                        # No parent means no particle birth; never pass a zero-life
                        # sentinel to decay or sequence-lifetime evaluation.
                        continue
                    origin,velocity=inherited_motion(*inherited,tick,scale)
                    positions[birth.index]=Vector(origin)
                    states[birth.index]['velocity']+=Vector(velocity)
                if parent_attributes:
                    inherited_values=[]
                    for operation in parent_attributes:
                        value=operation.initialize(parent_context.scalar_values(operation.field,parent_clock),
                            rng.random() if operation.random else None)
                        if value is not None:
                            if operation.field==1:life=value
                            else:
                                if value<0:raise ValueError('Negative inherited parent radius remains unsupported')
                                states[birth.index]['radius']=value
                        inherited_values.append(dict(field=operation.field,value=value))
                    samples=record.setdefault('parent_attribute_birth_samples',[])
                    if len(samples)<8:samples.append(dict(birth_index=birth.index,parent_clock=parent_clock,values=inherited_values))
                    if life<=0:
                        del states[birth.index];del ranges[birth.index]
                        continue
                sequence_life=next((m['parameters'] for m in enabled(definition,'initializers') if m['function']=='lifetime from sequence'),None)
                if sequence_life is not None and sheet:
                    from particle_sheet import sequence_lifetime
                    life=sequence_lifetime(sheet,states[birth.index]['sequence'],sequence_life)
                ranges[birth.index]=(life,states[birth.index]['radius'])
                if model_context is not None:
                    positions[birth.index]=Vector(model_context.birth(birth,rng,segments,life,velocity=tuple(states[birth.index]['velocity']),offset=tuple(states[birth.index]['offset'])))
                    # Model history now owns the pass-two spawn offset. The
                    # analytic appearance/motion state must not add it again.
                    states[birth.index]['offset']=Vector((0,0,0))
                fades[birth.index]=birth_fades(definition,rng)
                if partial_lock:
                    from particle_partial_lock import sampled_fades
                    lock_fades[birth.index]=sampled_fades(lock,rng.random(),rng.random())
                if pull_lock_active:
                    from particle_partial_lock import sampled_fades
                    attachment=parameters(definition,'operators','Movement Lock to Control Point')
                    if sampled_fades(attachment,.5,.5)!=(1.,1.):
                        states[birth.index]['translation_lock_fade']=sampled_fades(attachment,rng.random(),rng.random())
                        record['sampled_force_attachment_fade']=True
                if cull_history is not None:cull_history.add(birth,life)
                active_birth_capacity.add(birth.simulation_time,life,birth.index)
            if parent_updates:
                if locked_control is not None or model_context is not None or plane_controls or collision_config is not None or cull_history is not None:
                    raise ValueError('Parent update combined with locks, models or collisions requires ordered integration')
                from particle_parent_update import History as ParentUpdateHistory
                from particle_clock_inverse import real_time
                from particle_sim import simulation_at
                # Bind each definition's clocks/context; later graph nodes must
                # not replace callbacks retained by earlier parent collections.
                def parent_update_snapshot(clock,dt,child_segments=segments,parent=parent_context):
                    when=real_time(child_segments,clock,side='right')
                    before=real_time(child_segments,max(0.,clock-dt),side='right')
                    parent_clock=simulation_at(parent.segments,when)
                    parent_dt=max(0.,parent_clock-simulation_at(parent.segments,before))
                    return parent.snapshot(parent_clock,parent_dt)
                kept_updates=[birth for birth in births if birth.index in states]
                update_history=ParentUpdateHistory(parent_updates,kept_updates,
                    {birth.index:ranges[birth.index][0] for birth in kept_updates},
                    {birth.index:tuple((positions[birth.index][i]+states[birth.index]['offset'][i])/scale for i in range(3)) for birth in kept_updates},
                    {birth.index:tuple(v/scale for v in states[birth.index]['velocity']) for birth in kept_updates},
                    parent_update_snapshot,seed=particle_seed(descriptor,definition))
                original_evaluate_birth=evaluate_birth
                def updated_birth(birth,age,lifetime,history=update_history,original=original_evaluate_birth,origins=positions,unit=scale):
                    _,rgb,alpha,theta=original(birth,age,lifetime)
                    world=history.position(birth,age)
                    return Vector(world)*unit-origins[birth.index],rgb,alpha,theta
                evaluate_birth=updated_birth
            if (simulation_contexts is not None and definition.get('instance_id') not in simulation_contexts
                    and retain(definition.get('instance_id'),required_parent_ids,simulation_only,retain_leaf_contexts)):
                instance=definition.get('instance_id')
                from particle_decay_experimental import requires_extended_history
                delayed_history=requires_extended_history(definition['modules']['operators'],experimental_decay)
                if instance is not None and not plane_controls and collision_config is None and not delayed_history:
                    from particle_parent_collection import Collection
                    sampler=evaluate_birth
                    if partial_lock:
                        from particle_lock_transform import bind_partial_sampler
                        sampler=bind_partial_sampler(sampler,locked_control,scene,segments,lock_fades,lock_threshold,lock_clock,shot.start,fps,scale,vector=Vector)
                    elif locked_control:
                        from particle_lock_transform import bind_sampler,bind_matrix_query
                        from particle_clock_inverse import real_time
                        matrix_query=bind_matrix_query(locked_control,scene,
                            lambda birth,age,clock_segments=segments:real_time(clock_segments,birth.simulation_time+age,side='right',minimum_time=birth.time),
                            shot.start,fps)
                        sampler=bind_sampler(sampler,positions,locked_births,matrix_query,lock.get('lock rotation',False),vector=Vector)
                    kept=[birth for birth in births if birth.index in states]
                    def parent_radius(birth,age,life,d=definition,ranges=ranges,fades=fades,states=states,signed=bool(config.get('experimental_ring'))):
                        return appearance(d,age,life,ranges[birth.index][1],fades[birth.index],allow_signed_radius=signed,
                            creation_time=birth.simulation_time,oscillation_samples=states[birth.index].get('scalar_oscillations'))[0]
                    context=Collection(instance,kept,{birth.index:ranges[birth.index][0] for birth in kept},positions,sampler,scale,deaths=cull_history,radius_sampler=parent_radius)
                    context.segments=segments
                    simulation_contexts[instance]=context
            if child_cp_config is not None:
                context=simulation_contexts.get(definition.get('instance_id'))
                if context is None:raise ValueError('Child-control-point writer requires complete parent motion history')
                from particle_child_cp_blender import overlay as child_cp_overlay
                cp_environments[definition.get('instance_id')]=child_cp_overlay(context,child_cp_config,
                    descriptor,control_objects,scene,shot.start,fps,scale,set_time)
            if simulation_only:
                if definition.get('instance_id') not in simulation_contexts:
                    raise ValueError('Rendererless controller requires unsupported motion history')
                record.update(simulated=True,births=len(kept),simulation_only=True,approximate=True)
                records.append(record)
                continue
            color=definition['parameters'].get('color',[255,255,255,255])
            rgb=[c/255/12.92 if c/255<=.04045 else ((c/255+.055)/1.055)**2.4 for c in color[:3]]
            meshes=0;quads=0;nondegenerate_faces=0
            decay=next((m['parameters'] for m in enabled(definition,'operators') if m['function']=='Lifespan Decay'),None)
            if experimental_decay and decay is not None:
                particle_samples=((i,frame,time,None) for i,(frame,time) in enumerate(zip(particle_frames,particle_seconds)))
            else:
                from particle_sim import active_frame_samples
                particle_samples=active_frame_samples(births,segments,particle_frames,particle_seconds,
                    {index:value[0] for index,value in ranges.items()})
            for sample_index,frame,time,scheduled_alive in particle_samples:
                if progress and (sample_index%30==0 or sample_index==len(particle_frames)-1):
                    progress(f'{system.name} / {definition["name"]}: particle frames {sample_index+1}/{len(particle_frames)}')
                if not shot.value(system,'visible',float(time),True):continue
                if experimental_decay and decay is not None:
                    from particle_decay_experimental import living as delayed_living
                    alive=delayed_living([b for b in births if b.index in ranges],segments,float(time),{index:value[0] for index,value in ranges.items()},decay)
                    record['experimental_delayed_decay']=True
                else:
                    alive=scheduled_alive
                if not alive:continue
                set_time(float(time));camera=scene.camera.matrix_world.to_quaternion()
                right=camera@Vector((1,0,0));up=camera@Vector((0,1,0));normal=camera@Vector((0,0,1))
                orientation_rotation=orientation_control.matrix_world.to_quaternion() if orientation_control else None
                if config['orientation']==1 and not config.get('spritecard_geometry'):
                    from particle_orientation import upright_normal
                    normal=Vector(upright_normal(scene.camera.matrix_world.translation))
                if config['orientation']==2:normal=orientation_rotation@Vector((0,0,1)) if orientation_rotation else Vector((0,0,1))
                vertices=[];faces=[];colors=[];outline_colors=[];uv_coordinates=[];rope_points=[];rope_widths=[];rope_colors=[]
                dual_uvs={};dual_blends=[[],[]]
                if config.get('dual_sequence'):
                    from particle_dual_sequence_material import UV_NAMES
                    dual_uvs={name:[] for name in UV_NAMES}
                for birth,age in alive:
                    lifetime,initial_radius=ranges[birth.index]
                    if cull_history is not None and not cull_history.alive(birth.index,birth.simulation_time+age):continue
                    if collision_config is not None:
                        if birth.index not in collision_histories:
                            from particle_collision_history import KillHistory
                            def collision_position(t,b=birth,life=lifetime):
                                offset,_,_,_=evaluate_birth(b,t,life)
                                return tuple((positions[b.index][i]+offset[i])/scale for i in range(3))
                            def collision_radius(t,b=birth,life=lifetime,initial=initial_radius):
                                value,_=appearance(definition,t,life,initial,fades[b.index],creation_time=b.simulation_time,oscillation_samples=states[b.index].get('scalar_oscillations'))
                                return value*collision_config['radius scale']
                            collision_histories[birth.index]=KillHistory(collision_position,collision_radius,collision_trace)
                        is_alive=collision_histories[birth.index].alive(age)
                        set_time(float(time))
                        if not is_alive:continue
                    radius,alpha=appearance(definition,age,lifetime,initial_radius,fades[birth.index],allow_signed_radius=bool(config.get('experimental_ring')),creation_time=birth.simulation_time,oscillation_samples=states[birth.index].get('scalar_oscillations'))
                    states[birth.index]['creation_simulation_time']=birth.simulation_time
                    offset,particle_rgb,particle_alpha,theta=evaluate_birth(birth,age,lifetime);r=radius*scale
                    if any(m['function']=='Oscillate Scalar' and m['parameters'].get('oscillation field',7)==7 for m in enabled(definition,'operators')):
                        from particle_alpha_history import alpha as sampled_alpha
                        particle_alpha=sampled_alpha(definition,states[birth.index],age,lifetime,fades[birth.index])
                        alpha=1.
                    elif any(m['function']=='Remap Scalar' for m in enabled(definition,'operators')):
                        from particle_scalar_remap import ordered_alpha
                        particle_alpha=ordered_alpha(definition,states[birth.index],age,lifetime,fades[birth.index])
                        alpha=1.
                    if secondary_operators:
                        from particle_secondary_alpha import History as SecondaryHistory
                        if birth.index not in secondary_histories:
                            secondary_histories[birth.index]=SecondaryHistory(secondary_operators,birth.simulation_time,initial=states[birth.index].get('secondary_alpha',1.))
                        particle_alpha*=secondary_histories[birth.index].query(age)
                    else:particle_alpha*=states[birth.index].get('secondary_alpha',1.)
                    x=(right*math.cos(theta)+up*math.sin(theta))*r
                    y=(-right*math.sin(theta)+up*math.cos(theta))*r
                    source_center=positions[birth.index]+offset
                    if locked_control:
                        birth_position,birth_rotation=locked_births[birth.index]
                        if partial_lock:
                            from particle_partial_lock import history_displacement
                            received=history_displacement(segments,birth,float(time),lifetime,lock_fades[birth.index],lock_position,lock_threshold,
                                                          prepared_inverse=lock_clock)
                            source_center+=Vector(received)*scale
                            set_time(float(time))
                        else:
                            from particle_lock_transform import center as locked_center
                            source_center=locked_center(source_center,locked_control.matrix_world,birth_position,birth_rotation,lock.get('lock rotation',False))
                    if color_light_config:
                        from particle_color_lights import color as light_color
                        from particle_color_order import evaluate as ordered_color
                        from particle_sprite_state import linear_color
                        particle_rgb=ordered_color(definition['modules']['operators'],states[birth.index]['rgb'],age/lifetime,linear_color,
                            lambda incoming:light_color(color_light_config,tuple(v/scale for v in source_center),incoming,{cp:tuple(v/scale for v in obj.matrix_world.translation) for cp,obj in light_controls.items()}))
                    for plane,plane_control in plane_controls:
                        from particle_plane import world_plane,project
                        point,plane_normal=world_plane(plane,tuple(tuple(row) for row in plane_control.matrix_world.to_quaternion().to_matrix()),plane_control.matrix_world.translation,scale)
                        source_center=Vector(project(source_center,r,point,plane_normal))
                    if config['renderer']=='render_rope':
                        rope_points.append(tuple(source_center));rope_widths.append(r);rope_colors.append((*particle_rgb,alpha*particle_alpha))
                        continue
                    # Source adds screen-space sprites even when coplanar. Cycles
                    # ray intersections need distinct planes to avoid dark seams.
                    epsilon=max(1e-6,max(abs(c) for c in source_center)*2e-7)
                    rank=depth_ranks.get(int(frame),0);depth_ranks[int(frame)]=rank+1
                    center=source_center+normal*(rank*epsilon);index=len(vertices)
                    if config['renderer']=='render_sprite_trail':
                        renderer=parameters(definition,'renderers','render_sprite_trail')
                        from particle_oscillation import trail_duration
                        duration=trail_duration(definition,states[birth.index]['trail_duration'],age)
                        if any(m['function']=='Remap Scalar' and m['parameters']['output field']==10 for m in enabled(definition,'operators')):
                            from particle_radius_remap import scalar_state
                            _,duration=scalar_state(enabled(definition,'operators'),age,lifetime,initial_radius,birth.simulation_time,initial_trail=states[birth.index]['trail_duration'])
                        previous=evaluate_birth(birth,max(0.,age-duration),lifetime)[0]
                        delta=offset-previous
                        if locked_control:
                            # Include the authored control's world motion in both
                            # endpoints, rather than rotating only local motion.
                            from particle_trail_history import previous_time
                            history_time=previous_time(segments,birth,float(time),age,duration)
                            set_time(history_time)
                            history_matrix=locked_control.matrix_world.copy()
                            set_time(float(time))
                            birth_position,birth_rotation=locked_births[birth.index]
                            previous_center=positions[birth.index]+previous
                            from particle_lock_transform import center as locked_center
                            previous_center=locked_center(previous_center,history_matrix,birth_position,birth_rotation,lock.get('lock rotation',False))
                            delta=source_center-previous_center
                        elif delta.length<=1e-9:
                            from particle_trail_velocity import displacement as trail_displacement
                            lookback=min(max(0.,age),max(0.,duration))
                            estimated,used=trail_displacement(delta,states[birth.index]['velocity'],lookback)
                            if used:
                                delta=Vector(estimated)
                                record['trail_velocity_fallback_samples']=record.get('trail_velocity_fallback_samples',0)+1
                        direction=delta.normalized() if delta.length>1e-9 else up
                        length=min(float(renderer.get('max length',2000))*scale,max(float(renderer.get('min length',0))*scale,delta.length))
                        fade=float(renderer.get('length fade in time',0))
                        if fade>0:length*=min(1.,age/fade)
                        if length<=1e-9 or abs(r)<=1e-9:continue
                        if config['cpu_trail_geometry']:
                            from particle_trail_geometry import corners as trail_corners
                            quad=trail_corners(center,-direction*length,r,scene.camera.matrix_world.translation,
                                               bool(renderer.get('constrain radius to length',True)))
                            if not quad:continue
                            vertices.extend(quad)
                        else:
                            side=direction.cross(normal)
                            side=(side.normalized() if side.length>1e-8 else right)*r
                            tail=center-direction*length
                            vertices.extend((tail-side,tail+side,center+side,center-side))
                    elif config.get('spritecard_geometry'):
                        from particle_spritecard_geometry import corners as spritecard_corners
                        from particle_yaw import value as particle_yaw_at_age
                        vertices.extend(spritecard_corners(center,r,theta,particle_yaw_at_age(definition,states[birth.index],age,lifetime),
                            config['orientation'],scene.camera.matrix_world.translation,
                            (right,up,camera@Vector((0,0,1)))))
                    elif config['orientation']==1:
                        from particle_orientation import upright_corners
                        vertices.extend(upright_corners(center,r,theta,scene.camera.matrix_world.translation))
                    elif config['orientation']==2:
                        from particle_orientation import world_corners
                        if orientation_rotation:
                            vertices.extend(center+orientation_rotation@Vector(p) for p in world_corners((0,0,0),r,theta))
                        else:vertices.extend(world_corners(center,r,theta))
                    else:vertices.extend((center-x-y,center+x-y,center+x+y,center-x+y))
                    faces.append(tuple(range(index,index+4)))
                    from particle_sprite_state import sprite_uvs
                    # SpriteCard consumes yaw in its vertex math; the traced CPU
                    # upright/ground paths ignore yaw. Preserve the prior UV
                    # approximation for untraced CPU billboards and trails.
                    legacy_uv_flip=not config['cpu_trail_geometry'] and (config['renderer']!='render_animated_sprites' or
                                    (not config.get('spritecard_geometry') and config['orientation']==0))
                    if config.get('dual_sequence'):
                        from particle_dual_sequence import sample as sample_dual
                        sample_uvs,sample_blends=sample_dual(config['dual_sequence'],sheet,states[birth.index],age,dual_tables)
                        for name,values in dual_uvs.items():values.extend(sample_uvs[name.removeprefix('sfm_')])
                        for values,value in zip(dual_blends,sample_blends):values.extend([value]*4)
                        uv_coordinates.extend(sample_uvs['primary_current'])
                    else:
                        uv_coordinates.extend(sprite_uvs(coordinates(sheet,states[birth.index]['sequence'],age,lifetime,renderer,record.setdefault('limitations',[])),
                            states[birth.index]['yaw_flip'] if legacy_uv_flip else False))
                    colors.extend([(*particle_rgb,alpha*particle_alpha)]*4)
                    if material.get('sfm_particle_distance_alpha'):
                        from particle_distance_alpha import shader_color
                        outline_colors.extend([(*shader_color(states[birth.index].get('outline_rgb',(1,1,1))),states[birth.index].get('outline_alpha',1.))]*4)
                if config['renderer']=='render_rope':
                    if experimental_spline and material.get('sfm_particle_material_spline_type',0)==1:
                        if len(rope_points)<2:continue
                        from particle_spline import mesh_geometry,longitudinal_coordinates,shader_color
                        subdivisions=int(renderer['subdivision_count'])
                        image=next((node.image for node in material.node_tree.nodes if node.type=='TEX_IMAGE' and node.image),None)
                        if image is None:raise ValueError('Spline UV mapping requires a material texture')
                        along=longitudinal_coordinates(rope_points,subdivisions,float(renderer['texel_size'])/scale,float(time-shot.start),float(renderer['texture_scroll_rate']),float(renderer['texture_offset']),int(image.size[1]))
                        vertices,faces,uv_coordinates,colors=mesh_geometry([(*point,width) for point,width in zip(rope_points,rope_widths)],[shader_color(c) for c in rope_colors],subdivisions,tuple(scene.camera.matrix_world.translation),along,radius_trail_fade=float(material.get('sfm_particle_material_radius_trail_fade',1)),alpha_trail_fade=float(material.get('sfm_particle_material_alpha_trail_fade',1)),scale=1.)
                        record['decoded_spline_vertex_color_power']=2.2
                        record['experimental_spline_geometry']=True
                        record['source_spline_visual_parity_verified']=False
                    else:
                        from particle_rope import ribbon,subdivide
                        rope_points,rope_widths,rope_colors=subdivide(rope_points,rope_widths,rope_colors,int(renderer.get('subdivision_count',0)))
                        vertices,faces,uv_coordinates,colors=ribbon(rope_points,rope_widths,rope_colors,tuple(normal),float(renderer.get('texel_size',1))*scale,float(renderer.get('texture_scroll_rate',0))*float(time-shot.start)+float(renderer.get('texture_offset',0)))
                    if not faces:continue
                if not faces:continue
                mesh=bpy.data.meshes.new(definition['name']+f' frame {frame}');mesh.from_pydata(vertices,[],faces)
                nondegenerate_faces+=sum(p.area>0 for p in mesh.polygons)
                mesh.materials.append(material);uv=mesh.uv_layers.new()
                for corner,value in zip(uv.data,uv_coordinates):corner.uv=value
                if dual_uvs:
                    for name,values in dual_uvs.items():
                        layer=mesh.uv_layers.new(name=name)
                        for item,value in zip(layer.data,values):item.uv=value
                    from particle_dual_sequence_material import BLEND_NAMES
                    for name,values in zip(BLEND_NAMES,dual_blends):
                        attribute=mesh.attributes.new(name,'FLOAT','CORNER')
                        for item,value in zip(attribute.data,values):item.value=value
                if outline_colors:
                    from particle_distance_alpha import ATTRIBUTE
                    outline=mesh.color_attributes.new(name=ATTRIBUTE,type='FLOAT_COLOR',domain='CORNER')
                    outline.data.foreach_set('color',[v for color in outline_colors for v in color])
                rgba=mesh.color_attributes.new(name='sfm_particle_color',type='FLOAT_COLOR',domain='CORNER')
                for item,color_value in zip(rgba.data,colors):item.color=color_value
                obj=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(obj)
                obj['sfm_baked_particle_effect']=definition['name'];obj['sfm_baked_frame']=int(frame)
                from particle_identity import tag
                tag(obj,definition)
                if definition.get('renderer_pass_count',1)>1:
                    obj['sfm_particle_renderer_pass']=definition['renderer_pass_index']
                    obj['sfm_particle_renderer_function']=config['renderer']
                curves=curves_factory(obj,obj.name+' visibility')
                for attribute in ('hide_render','hide_viewport'):
                    curves.add(attribute,[0,int(frame),particle_next_frames[int(frame)]],[True,False,True],interpolation='CONSTANT')
                meshes+=1;quads+=len(faces)
            fade_values=[value for birth in fades.values() for value in birth.values()]
            record.update(rendered=True,approximate=True,births=len(births),frame_meshes=meshes,total_quads=quads,lifetime_range=config['lifetime_range'],radius_range=config['radius_range'],
                          sampled_fade_duration_range=[min(fade_values),max(fade_values)] if fade_values else None,
                          depth_separation=('minimal camera-axis epsilon for SpriteCard modes 0/1; ground-axis epsilon for mode 2; actual tilted plane normal is not used'
                                            if config.get('spritecard_geometry') else
                                            'minimal sprite-plane-normal epsilon for coincident sprites' if config['orientation'] in (1,2) else 'minimal camera-facing epsilon for coincident sprites'))
            record['texture_sheet_sequences']=len(sheet)
            record['rotation_lock_baked']=bool(lock and lock.get('lock rotation',False))
            record['trail_control_motion_baked']=bool(lock and config['renderer']=='render_sprite_trail')
            if config['cpu_trail_geometry']:
                record['trail_geometry']='Installed CPU corner layout: signed half-width, perspective side, current-to-tail UV order'
                record['trail_radius_length_constraint']=bool(renderer.get('constrain radius to length',True))
            record['initial_particles']=config['initial_particles']
            record['initial_particle_creation_time']=initial_time
            record['initial_particles_created']=sum(i<config['initial_particles'] for i in ranges) if initial_time is not None else 0
            record['birth_distribution']={
                'lifetime_exponent':config['lifetime_exponent'],
                'radius_exponent':config['radius_exponent'],
                'sampled_lifetime_range':[min(v[0] for v in ranges.values()),max(v[0] for v in ranges.values())] if ranges else None,
                'sampled_radius_range':[min(v[1] for v in ranges.values()),max(v[1] for v in ranges.values())] if ranges else None,
                'source_random_stream_parity':False}
            sequence_life=next((m['parameters'] for m in enabled(definition,'initializers') if m['function']=='lifetime from sequence'),None)
            if sequence_life is not None:
                record['sequence_lifetime']={'frames_per_second':float(sequence_life.get('Frames Per Second',30)),'applied':bool(sheet),'fallback_reason':None if sheet else 'No texture sheet; preserving previously initialized lifetime','sampled_lifetimes':sorted({life for life,radius in ranges.values()}),'source_visual_parity_verified':False}
            record['child_delay']=float(definition.get('child_delay',0))
            record['geometry_generated']=meshes>0
            record['nondegenerate_faces']=nondegenerate_faces
            record['degenerate_faces']=quads-nondegenerate_faces
            record['renderable_geometry_generated']=nondegenerate_faces>0
            if meshes and not nondegenerate_faces:
                record.update(rendered=False,failure_category='degenerate_particle_geometry',reason='All sampled particle faces have zero area; no renderable surface was generated')
            if any(m['function']=='Remap Scalar' and m['parameters']['output field']==3 for m in enabled(definition,'operators')):
                record['limitations'].append('Radius remaps replay with scales and oscillation in authored order on an approximate birth-relative 120 Hz clock; creation time remains system-relative. Source tick phase and exact visual parity are unverified.')
            if any(m['function']=='Remap Scalar' and m['parameters']['output field']==10 for m in enabled(definition,'operators')):
                record['limitations'].append('Trail-duration remaps consume ordered radius/trail state on an approximate birth-relative 120 Hz clock; Source tick phase and exact trail shading are unverified.')
            record['visible_sample_count']=sum(bool(shot.value(system,'visible',float(t),True)) for t in particle_seconds)
            if collision_config is not None:
                record['collision_deaths']=sum(h.death_age is not None for h in collision_histories.values())
                record['collision_histories']=len(collision_histories)
            if not meshes:
                record['empty_geometry_reason']='System hidden at every sampled time' if not record['visible_sample_count'] else 'No living particles at the sampled visible times'
            if particle_frame_step>1:
                record.setdefault('limitations',[]).append(f'Particle geometry is sampled every {particle_frame_step} timeline frames and held between samples; brief births, deaths and motion between samples can be missed.')
            if model_context is not None:
                record['model_hitbox_history_snapshots']=sum(len(h.times) for h in model_context.histories.values())
                if model_context.motion_histories:
                    record['model_bone_motion_snapshots']=sum(len(h.snapshots.times) for h in model_context.motion_histories.values())
                record['shared_model_pose_evaluations']=model_context.pose_cache.evaluations
            record['limitations']=record.get('limitations',[])+['Source RNG/tick phase and analytic drag/fade easing are approximate','Texture sheets use stepped frame selection; playback rate interpretation, cross-frame and multi-texture blending are not verified against Source']
            repeated_offsets=[m for m in enabled(definition,'initializers') if m['function']=='Position Modify Offset Random']
            if len(repeated_offsets)>1:
                record['ordered_repeated_initializers']={'Position Modify Offset Random':len(repeated_offsets)}
                record['limitations'].append('Repeated Position Modify Offset Random initializers are sampled and applied in authored order; Source random-stream parity is unverified')
            if cull_history is not None:
                record['plane_culling']['killed_births']=sum(cull_history.time(b.index) is not None for b in births if b.index in states)
            if record.get('experimental_delayed_decay'):
                record['limitations'].append('Experimental step-gated lifespan decay uses continuous collection time; Source engine-tick activation and visual parity are unverified')
            if lock and config['renderer']=='render_sprite_trail':record['limitations'].append('Trail endpoints sample the full locked control transform over simulation-age history; exact Source per-tick trail history is unverified')
            if definition.get('renderer_pass_count',1)>1:record['limitations'].append('Each renderer independently bakes the shared seeded particle simulation; Source renderer composition and depth ordering remain approximate')
            if any(any(float(m['parameters'].get(k,0))!=0 for k in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout')) for m in enabled(definition,'emitters')):record['limitations'].append('Emitter strength uses non-overlapping linear fades on collection simulation time; exact Source interpolation and tick scheduling are unverified')
            if len(enabled(definition,'emitters'))>1:record['limitations'].append('Multiple emitters merge chronological births with shared capacity; Source simultaneous birth order and random streams remain approximate')
            if any(m['function']=='Position On Spiral Sphere' for m in enabled(definition,'initializers')):
                record['limitations'].append('Spiral sphere uses zero initial speed, no CP scale override and an algebraic birth counter. Source context resets, accumulated float/trig rounding, random streams and tick timing remain approximate.')
            if any(m['function']=='Position From Chaotic Attractor' for m in enabled(definition,'initializers')):
                record['limitations'].append('Chaotic attractor preserves ordered recurrence from zero context. Source context resets, float/trig rounding, random integer stream and initializer ordering remain approximate.')
            if config['initial_particles']:record['limitations'].append('Initial particles are born at collection creation before emitter births; Source tick and random stream ordering are unverified')
            if lock and lock.get('lock rotation',False):record['limitations'].append('Full control-point rotation lock applies the birth-to-current rigid transform; Source per-tick physics/operator ordering and sprite-normal behavior are unverified')
            if any(m['function']=='Position Modify Offset Random' and m['parameters'].get('offset proportional to radius 0/1',False) for m in enabled(definition,'initializers')):record['limitations'].append('Spawn offsets scale by birth radius with preceding scalar remaps; Source initializer scheduling and random stream parity are unverified')
            if path_controls:record['limitations'].append('Straight sequential path uses birth-index endpoint mapping; Source endpoint phase and rejected-birth sequence behavior are unverified')
            if config['renderer']=='render_rope':
                record['rope_subdivision_count']=int(renderer.get('subdivision_count',0))
                record['limitations'].append('Rope is a camera-facing ribbon in birth order with clamped Catmull-Rom interpolation; Source subdivision count interpretation, spline endpoints, UV scale and scrolling phase are approximate')
            if config['renderer']=='render_sprite_trail':record['limitations'].append('Trails use sampled duration and analytic velocity ribbons; Source trail shading is approximate')
            if record.get('trail_velocity_fallback_samples'):
                record['limitations'].append('Zero-displacement trails estimate endpoint from initial velocity times lookback; Source trail renderer motion semantics are unverified')
            if any(m['function']=='Velocity Noise' for m in enabled(definition,'initializers')):record['limitations'].append('Velocity Noise samples the configured output range at birth; Source spatial/time noise correlation is not reproduced')
            if any(m['function']=='Velocity Random' for m in enabled(definition,'initializers')):record['limitations'].append('Velocity Random adds isotropic speed and authored local vector ranges captured at birth; Source random stream, spherical distribution and initializer combination/order are unverified')
            if any(m['function']=='Oscillate Scalar' for m in enabled(definition,'operators')):record['limitations'].append('Sprite radius/roll/alpha use the inspected parabolic oscillation wave with persistent birth-sampled converter random values on an approximate 120 Hz clock; alpha fades write from birth opacity. Source RNG alignment, tick timing, fade interaction and visual parity remain unverified')
            if any(m['function']=='Oscillate Vector' for m in enabled(definition,'operators')):record['limitations'].append('Vector position/RGB oscillation uses ordered current/previous-position history and clamped color writes on an approximate 120 Hz birth clock; drag follows the installed rounded log/exp formula. Converter birth samples and random-force ticks do not reproduce Source RNG identity; shared strength timing and visual parity remain unverified')
            if any(m['function']=='Oscillate Scalar Simple' and m['parameters'].get('oscillation field',7)!=16 for m in enabled(definition,'operators')):record['limitations'].append('Simple scalar oscillation uses integrated sinusoidal size/opacity/trail-duration changes; Source phase, tick integration and operator ordering fidelity are not verified')
            if secondary_operators:record['limitations'].append('Secondary opacity uses collection-time parabolic oscillation and ordered per-tick clamping, multiplied by primary opacity. The 120 Hz clock phase and Source visual parity remain approximate; timed strengths are unsupported.')
            if any(m['function']=='random force' for m in enabled(definition,'forces')):record['limitations'].append('Random forces use independent 60 Hz samples per particle; Source RNG/tick correlation is not reproduced')
            if any(m['function']=='Radius Scale' for m in enabled(definition,'operators')):
                mixed_radius=any(m['function']=='Oscillate Scalar Simple' and int(m['parameters'].get('oscillation field',7))==3 for m in enabled(definition,'operators'))
                record['limitations'].append('Radius scales and radius oscillation replay in authored order on an approximate birth-relative 120 Hz clock; Source oscillation phase and tick integration remain unverified' if mixed_radius else 'Radius scales write from birth radius in authored order and hold inactive values on an approximate birth-relative 120 Hz clock; Source tick phase remains unverified')
            if any(m['function']=='Rotation Spin Roll' for m in enabled(definition,'operators')):record['limitations'].append('Roll spin uses analytic linear slowdown and non-overlapping collection-clock strength fades; Source interpolation/tick parity is unverified')
            if any(m['function']=='Color Fade' and any(float(m['parameters'].get(k,0))!=0 for k in ('operator start fadein','operator end fadein','operator start fadeout','operator end fadeout')) for m in enabled(definition,'operators')):
                record['limitations'].append('Timed Color Fade uses the installed positive-strength activation gate and preserves inactive RGB on an approximate 120 Hz collection clock; Source tick phase and color-space parity remain unverified')
        except Exception as exc:
            record['reason']=str(exc)
            if progress:progress(system.name+' / '+definition['name']+': particle skipped: '+str(exc))
        records.append(record)
    scene.collection.children.link(collection)
    scene.frame_set(original_frame)
    return records




def bake(*args, **kwargs):
    from particle_bake_visibility import suspend_completed_sprites
    from particle_validation import annotate
    scene = args[3] if len(args) > 3 else kwargs['scene']
    with suspend_completed_sprites(scene):
        return [annotate(record) for record in _bake(*args, **kwargs)]

