"""Animated model placement and hitbox-follow history for native sprite baking.

Source random streams and simulation tick phase remain approximate. Other
position writers require their own ordered integration and are rejected here.
"""
import copy,math,random
from particle_model_state import State
from particle_model_history import History
from particle_model_selection import select
from particle_hitbox_lerp import weight

def prepare_definition(definition,descriptor):
    enabled=lambda group:[m for m in definition['modules'][group] if m['parameters'].get('operator enabled',True)]
    placements=[m for m in enabled('initializers') if m['function']=='Position on Model Random']
    follows=[m for m in enabled('operators') if m['function'] in ('Movement Lerp to Hitbox','Movement Lock to Bone')]
    if not placements and not follows:return None
    if len(placements)!=1 or len(follows)>1:raise ValueError('Model particles require one placement and at most one hitbox follow operator')
    position=placements[0]['parameters'];follow=follows[0]['parameters'] if follows else None
    cp=float(position.get('control_point_number',0))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<len(descriptor['control_models']):raise ValueError('Model particle control point has no attached model')
    if not descriptor['control_models'][int(cp)]:raise ValueError('Model particle control model is empty')
    select(position,1,random.Random(0)) # Validate authored selection without consuming bake RNG.
    if follow is not None:
        key='control_point_number' if follows[0]['function']=='Movement Lock to Bone' else 'control point number'
        if float(follow.get(key,0))!=cp or follow.get('hitbox set','default')!=position.get('hitbox set','default'):raise ValueError('Cross-model hitbox follow is unverified')
        if follows[0]['function']=='Movement Lerp to Hitbox':
            weight(.5,float(follow.get('lifetime lerp start',0)),float(follow.get('lifetime lerp end',1)),1.)
        else:
            from particle_bone_lock import weight as lock_weight
            lock_weight(.5,1/120,float(follow.get('lifetime fade start',0)),float(follow.get('lifetime fade end',0)))
            threshold=float(follow.get('instant jump threshold',100))
            if not math.isfinite(threshold) or threshold<0:raise ValueError('Invalid model jump threshold')
            if follow.get('rigid lock',False) not in (False,True,0,1):raise ValueError('Invalid rigid model lock')
    for module in placements+follows:
        p=module['parameters']
        defaults={'operator start fadein':0,'operator end fadein':0,'operator start fadeout':0,'operator end fadeout':0,'operator fade oscillate':0,
                  'operator time offset min':0,'operator time offset max':0,'operator time scale min':1,'operator time scale max':1,
                  'operator strength random scale min':1,'operator strength random scale max':1,'operator strength scale control point':-1,'operator end cap state':-1}
        if any(float(p.get(k,v))!=v for k,v in defaults.items()):raise ValueError('Model particle shared strength or timing is unverified')
    bone_lock=bool(follows and follows[0]['function']=='Movement Lock to Bone')
    ordinary={'Lifetime Random','Radius Random','Rotation Random','Rotation Speed Random','Rotation Yaw Flip Random','Color Random','Alpha Random','Sequence Random','Trail Length Random','lifetime from sequence','Position Modify Offset Random','Remap Control Point to Vector'}
    ordered_lerp=bool(follow is not None and any(m['function']=='Movement Basic' for m in enabled('operators')))
    if bone_lock or ordered_lerp:
        # Both velocity initializers have slot29=true in installed SFM, so they
        # modify previous position in pass two after model placement regardless
        # of their position in the authored initializer list.
        ordinary.update(('Velocity Random','Velocity Noise'))
    if any(m['function'] not in ordinary|{'Position on Model Random'} for m in enabled('initializers')):raise ValueError('Combined model placement and other spatial/field initializers require ordered history')
    nonspatial={'Lifespan Decay','Alpha Fade and Decay','Alpha Fade In Simple','Alpha Fade Out Simple','Alpha Fade In Random','Alpha Fade Out Random','Radius Scale','Rotation Basic','Rotation Spin Roll','Color Fade','Movement Lerp to Hitbox'}
    nonspatial.add('Movement Basic')
    for module in enabled('operators'):
        if module['function']=='Oscillate Scalar Simple':
            from particle_secondary_alpha import settings as secondary_settings
            secondary_settings(module['parameters'])
            nonspatial.add('Oscillate Scalar Simple')
    if bone_lock:nonspatial.add('Movement Lock to Bone')
    if any(m['function'] not in nonspatial for m in enabled('operators')) or enabled('forces') or enabled('constraints'):raise ValueError('Model follow with additional position/field writers requires ordered integration')
    if any(m['function']!='render_animated_sprites' for m in enabled('renderers')):raise ValueError('Model hitbox history currently requires animated sprite rendering')
    result=copy.deepcopy(definition)
    for module in result['modules']['initializers']:
        if module['function']=='Position on Model Random':
            module['function']='Position From Control Points';module['parameters']={'Starting Control Point':int(cp)}
    result['modules']['operators']=[m for m in result['modules']['operators'] if m['function'] not in ('Movement Lerp to Hitbox','Movement Lock to Bone')]
    ignored={}
    if any(float(v)!=0 for v in position.get('direction bias',(0,0,0))):ignored['direction bias']=list(position['direction bias'])
    if position.get('force to be inside model',0)!=0:ignored['force to be inside model']=position['force to be inside model']
    motion=[copy.deepcopy(m) for m in enabled('operators') if m['function'] in ('Movement Basic','Movement Lock to Bone','Movement Lerp to Hitbox')] if bone_lock or ordered_lerp else None
    return result,dict(control_point=int(cp),position=position,follow=follow,motion=motion,sfm_query_ignored_settings=ignored)

class Context:
    def __init__(self,binding,settings,scene,shot,fps,pose_cache=None):
        self.binding=binding;self.settings=settings;self.scene=scene;self.shot=shot;self.fps=fps
        self.states={};self.histories={};self.clocks={};self.limits={}
        self.motion_histories={};self.control_point_query=None
        from particle_model_pose_cache import PoseCache
        self.pose_cache=pose_cache or PoseCache(scene,shot,fps)
    def birth(self,birth,rng,segments,lifetime,velocity=(0,0,0),offset=(0,0,0)):
        import bpy
        from particle_clock_prepared import PreparedInverse
        state=State(self.binding,self.settings['position'],rng,bpy.context.evaluated_depsgraph_get())
        from particle_model_offset import apply as spawn_offset
        state.position,state.previous_position=spawn_offset(state.position,state.previous_position,offset)
        history=History();history.record(0.,state.position,state.previous_position)
        self.states[birth.index]=state;self.histories[birth.index]=history
        clock=PreparedInverse(segments);self.clocks[birth.index]=clock
        self.limits[birth.index]=min(lifetime,max(0.,clock.total-birth.simulation_time))
        if self.settings.get('motion'):
            needs_control=any(m['function']=='Movement Lock to Bone' for m in self.settings['motion'])
            if needs_control and self.control_point_query is None:raise ValueError('Bone-lock control point evaluator unavailable')
            from particle_model_motion import History as MotionHistory
            def time_at(age):return clock.query(birth.simulation_time+age,side='right',minimum_time=birth.time)
            def targets(operator,old,new):
                return tuple(self.pose_cache.point(self.binding,state.selection['index'],state.selection['relative'],time_at(age)) for age in (old,new))
            threshold=float(self.settings['follow'].get('instant jump threshold',100))*self.binding.scale
            def bypass(old,new):
                return math.dist(self.control_point_query(time_at(old)),self.control_point_query(time_at(new)))>threshold
            motion=copy.deepcopy(self.settings['motion'])
            for m in motion:
                if m['function']=='Movement Basic':
                    m['parameters']['gravity']=tuple(float(v)*self.binding.scale for v in m['parameters'].get('gravity',(0,0,0)))
            self.motion_histories[birth.index]=MotionHistory(motion,state.position,velocity,targets,maximum_age=self.limits[birth.index],bypass_at=bypass if needs_control else None)
        return state.position
    def query(self,birth,age):
        import bpy
        history=self.histories[birth.index];state=self.states[birth.index]
        if self.settings['follow'] is None:return state.position
        previous=self.scene.frame_current,self.scene.frame_subframe
        try:
            if birth.index in self.motion_histories:return self.motion_histories[birth.index].query(age)[0]
            while history.times[-1]<age:
                tick=math.floor(history.times[-1]*120+1e-8)+1
                following=min(tick/120.,self.limits[birth.index])
                if following<=history.times[-1]:raise ValueError('Model particle query exceeds its simulation clock')
                time=self.clocks[birth.index].query(birth.simulation_time+following,side='right',minimum_time=birth.time)
                target=self.pose_cache.point(self.binding,state.selection['index'],state.selection['relative'],time)
                state.lerp(following,None,self.settings['follow'],target=target)
                history.record(following,state.position,state.previous_position)
            return history.query(age)[0]
        finally:
            if (self.scene.frame_current,self.scene.frame_subframe)!=previous:
                self.scene.frame_set(previous[0],subframe=previous[1])

def factory(session,imported,assets,scene,shot,fps,scale):
    from particle_model_pose_cache import PoseCache
    pose_cache=PoseCache(scene,shot,fps)
    def bind(definition,descriptor):
        prepared=prepare_definition(definition,descriptor)
        if prepared is None:return definition,None
        result,settings=prepared;reference=descriptor['control_models'][settings['control_point']]
        identity=reference['id'];model=next(e for e in session.elements.values() if str(e.id)==identity)
        root=imported.get(identity)
        if root is None:raise ValueError('Attached particle model was not imported')
        armatures=[o for o in scene.objects if o.type=='ARMATURE' and o.parent==root]
        if len(armatures)!=1:raise ValueError('Attached model requires one imported armature')
        from model_hitboxes import read
        from model_hitbox_binding import Binding
        path=model['modelName'];buffer=assets.buffer(path)
        if buffer is None:raise FileNotFoundError(path)
        buffer.seek(0)
        raw=buffer.read()
        binding=Binding(armatures[0],assets.mdl(path),read(raw),set_name=settings['position'].get('hitbox set','default'),scale=scale)
        context=Context(binding,settings,scene,shot,fps,pose_cache)
        if settings.get('motion') and any(m['function']=='Movement Lock to Bone' for m in settings['motion']):
            cp_id=descriptor['control_points'][settings['control_point']]['id']
            controls=[o for o in scene.objects if o.get('sfm_transform_id')==cp_id]
            if len(controls)!=1:raise ValueError('Bone-lock control point requires one imported transform')
            control=controls[0];positions={}
            def query(time):
                import bpy
                from particle_target_time import cache_key
                key=cache_key(control.name,time,shot.start,fps)
                if key not in positions:
                    frame=1+(time-shot.start)*fps
                    scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
                    positions[key]=tuple(control.evaluated_get(bpy.context.evaluated_depsgraph_get()).matrix_world.translation)
                return positions[key]
            context.control_point_query=query
        return result,context
    return bind
