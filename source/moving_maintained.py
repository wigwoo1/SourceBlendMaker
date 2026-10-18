"""Bake translation of maintained-particle emitters at each slot's birth time.

Uses the maintained geometry evaluator for appearance and slot replacement.
Source random streams/tick boundaries remain approximate. No runtime handlers.
"""
import math
from particle_sim import simulation_at

def birth_clock(clock,lifetime,gates):
    candidates=[]
    for start,end in gates:
        if clock<start-1e-7:continue
        capped=min(clock,max(start,end-1e-7))
        candidates.append(start+math.floor((capped-start)/lifetime)*lifetime)
    return max(candidates) if candidates else None

def global_birth_time(segments,clock):
    for segment in segments:
        if not segment.simulating or segment.end<=segment.start:continue
        if simulation_at(segments,segment.start)-1e-7<=clock<=simulation_at(segments,segment.end)+1e-7:
            if simulation_at(segments,segment.start)>=clock:return segment.start
            a,b=segment.start,segment.end
            for _ in range(40):
                mid=(a+b)*.5
                if simulation_at(segments,mid)<clock:a=mid
                else:b=mid
            return (a+b)*.5
    raise ValueError('Particle birth clock lies outside the simulated interval')

def bake_frames(template,control,origin,system,definition,shot,scene,frames,seconds,segments,gates,curves_factory,offset_control=None):
    import bpy
    old_frame,old_subframe=scene.frame_current,scene.frame_subframe
    # Local offsets rotate at birth; local velocity needs separate handling.
    from particle_bake import enabled
    initial={m['function']:m['parameters'] for m in enabled(definition,'initializers')}
    offset=initial.get('Position Modify Offset Random',{})
    noise=initial.get('Velocity Noise',{})
    sphere=initial.get('Position Within Sphere Random',{})
    cache={};created=[]
    collection=bpy.data.collections.new(system.name+' moving maintained particles');scene.collection.children.link(collection)
    try:
        fps=(frames[-1]-frames[0])/(seconds[-1]-seconds[0]) if len(frames)>1 and seconds[-1]!=seconds[0] else scene.render.fps/scene.render.fps_base
        for sample_index,(frame,time) in enumerate(zip(frames,seconds)):
            if sample_index%max(1,len(frames)//20)==0:print(f'Particle {system.name}: baking moving emitter frame {frame} ({sample_index+1}/{len(frames)})',flush=True)
            if not shot.value(system,'visible',float(time),True):continue
            scene.frame_set(int(frame));depsgraph=bpy.context.evaluated_depsgraph_get()
            mesh=bpy.data.meshes.new_from_object(template.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph)
            life=mesh.attributes['sfm_life'];clock=simulation_at(segments,float(time))
            for index in range(0,len(mesh.vertices),4):
                birth=birth_clock(clock,life.data[index].value,gates)
                if birth is None:continue
                if birth not in cache:
                    global_time=global_birth_time(segments,birth);f=1+(global_time-shot.start)*fps
                    scene.frame_set(math.floor(f),subframe=f-math.floor(f))
                    cache[birth]=(control.matrix_world.translation.copy()-origin,
                                  offset_control.matrix_world.to_quaternion() if offset_control else None,control.matrix_world.to_quaternion())
                displacement,rotation,velocity_rotation=cache[birth]
                correction=displacement.copy()
                if sphere.get('bias in local system',False):
                    sphere_offset=mesh.attributes['sfm_sphere_offset'].data[index].vector
                    correction+=velocity_rotation@sphere_offset-sphere_offset
                local=mesh.attributes['sfm_local_velocity'].data[index].vector
                movement=next((m['parameters'] for m in enabled(definition,'operators') if m['function']=='Movement Basic'),{})
                age=max(0.,clock-birth);drag=max(0.,float(movement.get('drag',0)))
                velocity_time=-math.expm1(-drag*age)/drag if drag>1e-8 else age
                correction+=(velocity_rotation@local-local)*velocity_time
                if rotation is not None:
                    spawn_offset=mesh.attributes['sfm_spawn_offset'].data[index].vector
                    correction+=rotation@spawn_offset-spawn_offset
                for vertex in mesh.vertices[index:index+4]:vertex.co+=correction
            obj=bpy.data.objects.new(definition['name']+f' moving frame {frame}',mesh);collection.objects.link(obj);created.append(obj)
            obj['sfm_baked_particle_effect']=definition['name'];obj['sfm_baked_frame']=int(frame)
            from particle_identity import tag
            tag(obj,definition)
            curves=curves_factory(obj,obj.name+' visibility')
            for attribute in ('hide_render','hide_viewport'):curves.add(attribute,[0,int(frame),int(frame)+1],[True,False,True],interpolation='CONSTANT')
        return {'effect':definition['name'],'rendered':True,'approximate':True,'geometry_generated':bool(created),'method':'native per-frame moving maintained sprites','frame_meshes':len(created),'birth_positions':len(cache),'local_offset_rotation_baked':offset_control is not None,'local_velocity_rotation_baked':True,'limitations':['Emitter translation and local offset rotation are captured at slot birth; Source RNG/tick phase remains approximate','Slot lifetime/radius/fade/sequence samples repeat across replacement births','Per-frame geometry increases file size; motion blur between frame meshes is approximate']}
    finally:
        bpy.data.objects.remove(template,do_unlink=True)
        scene.frame_set(old_frame,subframe=old_subframe)
