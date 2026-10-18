"""Experimental unoccluded pass scene for Source ignore-depth refraction."""
def pass_scene(source,objects):
    import bpy
    scene=bpy.data.scenes.new(source.name+' ignore-depth refraction passes')
    scene.camera=source.camera;scene.world=source.world
    if source.camera:scene.collection.objects.link(source.camera)
    for obj in objects:
        if obj!=source.camera:scene.collection.objects.link(obj)
    scene.render.engine='CYCLES';scene.cycles.samples=source.cycles.samples
    for key in ('resolution_x','resolution_y','resolution_percentage','fps','fps_base'):
        setattr(scene.render,key,getattr(source.render,key))
    scene.render.film_transparent=True
    scene.frame_start=source.frame_start;scene.frame_end=source.frame_end
    scene.frame_set(source.frame_current,subframe=source.frame_subframe)
    return scene
