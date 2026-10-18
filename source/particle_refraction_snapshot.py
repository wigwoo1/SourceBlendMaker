"""Experimental evaluated mesh snapshots for maintained refraction geometry."""
def snapshot(scene,obj,frames,curves_factory):
    import bpy
    original_frame=scene.frame_current;original_subframe=scene.frame_subframe;created=[]
    try:
        for frame in frames:
            scene.frame_set(int(frame));bpy.context.view_layer.update()
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
            mesh.name=obj.name+f' refraction frame {frame}'
            copy=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(copy);copy.matrix_world=obj.matrix_world.copy()
            copy['sfm_baked_frame']=int(frame);copy['sfm_baked_particle_effect']=obj.get('sfm_particle_effect',obj.name)
            curves=curves_factory(copy,copy.name+' visibility')
            hidden=bool(obj.hide_render)
            for name in ('hide_render','hide_viewport'):
                curves.add(name,[0,int(frame),int(frame)+1],[True,hidden,True],interpolation='CONSTANT')
            created.append(copy)
    except Exception:
        for copy in created:
            mesh=copy.data;bpy.data.objects.remove(copy,do_unlink=True);bpy.data.meshes.remove(mesh)
        raise
    finally:scene.frame_set(original_frame,subframe=original_subframe)
    # Keep the editable procedural original for inspection without double rendering.
    collection=bpy.data.collections.new(obj.name+' procedural original');scene.collection.children.link(collection);collection.hide_render=True
    collection.objects.link(obj)
    for owner in list(obj.users_collection):
        if owner!=collection:owner.objects.unlink(obj)
    return created
