"""Experimental global per-frame depth ordering across baked refraction effects."""
def assign(scene,objects,camera):
    import json
    from collections import defaultdict
    from mathutils import Vector
    from particle_refraction_order import back_to_front
    from particle_refraction import blur_samples
    from particle_refraction_layers import isolate_material,register_layer
    frames=defaultdict(list)
    for obj in objects:
        frame=obj.get('sfm_baked_frame')
        if frame is None or len(obj.data.materials)!=1:raise ValueError('Expected original single-material baked frame mesh')
        base=obj.data.materials[0]
        if not base.get('sfm_refraction_experimental'):raise ValueError('Expected experimental Refract material')
        settings=json.loads(base['sfm_refraction_settings']);blur=settings['blur'];blur_samples(blur)
        if settings.get('has_unimplemented_proxies'):raise ValueError('Unsupported refraction material proxy')
        overlay=bool(settings.get('authored_shader_features',{}).get('ignore_depth'))
        frames[frame].append((obj,base,blur,overlay))
    original_frame=scene.frame_current;cache={};used=set()
    try:
        for frame,entries in frames.items():
            scene.frame_set(int(frame))
            faces=[(obj,base,blur,overlay,p) for obj,base,blur,overlay in entries for p in obj.data.polygons]
            centers=[obj.matrix_world@p.center for obj,base,blur,overlay,p in faces]
            forward=camera.matrix_world.to_quaternion()@Vector((0,0,-1))
            for rank,index in enumerate(back_to_front(centers,camera.matrix_world.translation,forward)):
                obj,base,blur,overlay,polygon=faces[index];name=f'rank_{rank}_blur_{blur}'+('_overlay' if overlay else '')
                key=(base.as_pointer(),rank,blur)
                if key not in cache:cache[key]=isolate_material(base,name)
                material=cache[key]
                slot=next((i for i,m in enumerate(obj.data.materials) if m==material),None)
                if slot is None:obj.data.materials.append(material);slot=len(obj.data.materials)-1
                polygon.material_index=slot;used.add((rank,blur,name,overlay))
    finally:scene.frame_set(original_frame)
    layers=[(name,blur,overlay) for rank,blur,name,overlay in sorted(used)]
    for name,blur,overlay in layers:register_layer(scene.view_layers[0],name)
    return layers
