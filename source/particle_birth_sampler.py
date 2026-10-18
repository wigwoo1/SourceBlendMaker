"""Bind one definition and its motion histories to a persistent sampler."""

def bind(*, states, plane_force_configs, experimental_pull, pull_modules, ordered_spatial, twist_modules, definition, positions, scale, record, plane_histories, evaluate, planned_definition, Vector, model_context, shot, pull_target_cache, segments, scene, prepared_clock, set_time, control_objects, descriptor, fps, pull_lock=False):
    from particle_bake import enabled, parameters
    def evaluate_birth(birth,age,lifetime):
        state=states[birth.index]
        state['creation_simulation_time']=birth.simulation_time
        plane_force_modules=plane_force_configs
        if (experimental_pull and pull_modules) or plane_force_modules or (ordered_spatial and twist_modules):
            from particle_pull_state_adapter import position as pull_position
            from particle_clock_inverse import real_time
            def target_at_clock(cp,clock):
                history_time=(prepared_clock.query(clock,side='right',minimum_time=birth.time) if prepared_clock is not None else real_time(segments,clock,side='right',minimum_time=birth.time))
                from particle_target_time import cache_key
                key=cache_key(cp,history_time,shot.start,fps)
                if key in pull_target_cache:return pull_target_cache[key]
                previous_frame,previous_subframe=scene.frame_current,scene.frame_subframe
                try:
                    set_time(history_time)
                    point=tuple(control_objects[descriptor['control_points'][cp]['id']].matrix_world.translation)
                    pull_target_cache[key]=point
                    return point
                finally:scene.frame_set(previous_frame,subframe=previous_subframe)
            if pull_lock:
                from particle_pull_lock_history import baked_position
                offset=Vector(baked_position(definition,state,age,lifetime,scale,positions[birth.index],target_at_clock))
                # Preserve authored indices used by sampled oscillation state.
                # Motion forces are already integrated by baked_position.
                appearance={**definition,'modules':{**definition['modules'],'forces':[],
                    'operators':[{**m,'parameters':{**m['parameters'],'operator enabled':False}}
                        if m['function']=='Movement Lock to Control Point' else m
                        for m in definition['modules']['operators']]}}
                _,rgb,alpha,theta=evaluate(appearance,state,age,lifetime,scale)
                return offset,rgb,alpha,theta
            if ordered_spatial:
                if '_spatial_acceleration' not in state:
                    from particle_spatial_force_context import bind
                    state['_spatial_acceleration']=bind(enabled(definition,'forces'),positions[birth.index],
                                                        scale,birth.simulation_time,target_at_clock)
                state['_ordered_force_history']=True
                record['ordered_spatial_force_history']=True
            elif plane_force_modules:
                motion=parameters(definition,'operators','Movement Basic')
                initial=tuple((positions[birth.index][i]+state['offset'][i])/scale for i in range(3))
                from particle_plane_force_history import History
                if birth.index not in plane_histories:
                    plane_histories[birth.index]=History(initial,tuple(v/scale for v in state['velocity']),plane_force_modules,
                        lambda cp,t:tuple(v/scale for v in target_at_clock(cp,t)),gravity=motion.get('gravity',(0,0,0)),drag=motion.get('drag',0),birth_clock=birth.simulation_time)
                result,_=plane_histories[birth.index].query(age)
                world=tuple(v*scale for v in result)
            else:world=pull_position(definition,state,age,scale,positions[birth.index],target_at_clock)
            if not ordered_spatial:
                offset,rgb,alpha,theta=evaluate(planned_definition,state,age,lifetime,scale)
                offset=Vector(world)-positions[birth.index]
                return offset,rgb,alpha,theta
        offset,rgb,alpha,theta=evaluate(planned_definition,state,age,lifetime,scale)
        if model_context is not None and model_context.settings['follow'] is not None:
            offset=Vector(model_context.query(birth,age))-positions[birth.index]
        return offset,rgb,alpha,theta

    return evaluate_birth
