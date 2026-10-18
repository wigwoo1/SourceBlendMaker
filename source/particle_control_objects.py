"""Create Blender transforms for particle control points outside the scene DAG."""


def import_missing(pending_particles, scene, shot, frames, seconds, animate_transform):
    """Bind every DMX control-point transform to a Blender object.

    SFM stores extra particle control points as DmeTransform elements in the
    particle system's controlPoints array. Unlike controlPoint0, they need not
    have a DmeDag in the scene hierarchy, so hierarchy import cannot create an
    object for them. The particle baker resolves controls by sfm_transform_id.
    """
    import bpy

    controls = {
        obj.get("sfm_transform_id"): obj
        for obj in scene.objects
        if obj.get("sfm_transform_id")
    }
    missing = []
    for system, _descriptor, _text in pending_particles:
        for index, transform in enumerate(system.get("controlPoints", [])):
            if transform is None:
                continue
            transform_id = str(transform.id)
            if transform_id in controls:
                continue
            missing.append((system, index, transform, transform_id))

    if not missing:
        return {"created": 0, "ids": []}

    collection = bpy.data.collections.new("SFM Particle Control Points")
    scene.collection.children.link(collection)
    created = []
    for system, index, transform, transform_id in missing:
        obj = bpy.data.objects.new(
            f"{system.name} {transform.name or f'controlPoint{index}'} transform",
            None,
        )
        collection.objects.link(obj)
        obj.empty_display_type = "PLAIN_AXES"
        obj.empty_display_size = 0.05
        obj.hide_render = True
        obj["sfm_transform_id"] = transform_id
        obj["sfm_particle_control_point"] = True
        obj["sfm_particle_system"] = system.name
        obj["sfm_control_point_index"] = index
        animate_transform(obj, shot, transform, frames, seconds)
        controls[transform_id] = obj
        created.append(transform_id)

    return {"created": len(created), "ids": created}
