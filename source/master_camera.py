"""Native master cameras retimed to sequencer shots without script handlers.

Ordinary cameras share their original actions through retimed NLA strips.
Cameras with constraints, drivers or focus targets are sampled instead.
"""
import math


def _complex_animation(owner):
    ad = owner.animation_data
    return ad is not None and (ad.drivers or ad.nla_tracks
                              or (ad.action and (ad.action_blend_type != 'REPLACE'
                                                or ad.action_influence != 1)))


def _chain(camera):
    result = []
    while camera is not None:
        if camera in result:
            raise ValueError('Camera has a cyclic parent hierarchy')
        result.append(camera)
        camera = camera.parent
    return result


def _share_action(source, target, start, end, source_start):
    source_ad = source.animation_data
    target.animation_data_clear()
    if source_ad is None or source_ad.action is None:
        return
    ad = target.animation_data_create()
    track = ad.nla_tracks.new()
    track.name = 'SFM master shot timing'
    strip = track.strips.new('Source camera animation', math.floor(start), source_ad.action)
    strip.action_slot = source_ad.action_slot
    strip.use_sync_length = False
    strip.action_frame_start = source_start
    strip.action_frame_end = source_start + end - start
    strip.frame_start = start
    strip.frame_end = end
    strip.blend_type = 'REPLACE'
    strip.extrapolation = 'HOLD'
    strip.blend_in = strip.blend_out = 0
    ad.use_nla = True


def _retimed_camera(camera, collection, name, start, end, source_start):
    copies = {}
    for source in reversed(_chain(camera)):
        obj = source.copy()
        if source == camera:
            obj.data = source.data.copy()
            _share_action(source.data, obj.data, start, end, source_start)
        obj.name = name if source == camera else name + ' / ' + source.name
        collection.objects.link(obj)
        obj.parent = copies.get(source.parent)
        _share_action(source, obj, start, end, source_start)
        copies[source] = obj
    return copies[camera]


_CAMERA_VALUES = ('lens', 'sensor_width', 'sensor_height', 'shift_x', 'shift_y',
                  'clip_start', 'clip_end', 'ortho_scale', 'dof.focus_distance',
                  'dof.aperture_fstop', 'dof.aperture_blades',
                  'dof.aperture_rotation', 'dof.aperture_ratio', 'dof.use_dof')


def _value(owner, path):
    for key in path.split('.'):
        owner = getattr(owner, key)
    return owner


def _set_frame(scene, frame):
    integer = math.floor(frame)
    scene.frame_set(integer, subframe=frame - integer)


def _baked_camera(camera, scene, collection, name, start, end, source_start, curves):
    import bpy
    if curves is None:
        from blender_worker import Curves as curves
    window = bpy.context.window
    previous = window.scene if window else None
    old_frame = scene.frame_current + scene.frame_subframe
    old_camera = scene.camera
    try:
        if window:
            window.scene = scene
        _set_frame(scene, source_start)
        obj = bpy.data.objects.new(name, camera.data.copy())
        collection.objects.link(obj)
        obj.data.animation_data_clear()
        obj.data.dof.focus_object = None
        obj.rotation_mode = 'QUATERNION'
        frames = [start + index for index in range(max(1, math.ceil(end - start)))]
        positions, rotations, scales = [], [], []
        values = {path: [] for path in _CAMERA_VALUES}
        last_rotation = None
        for frame in frames:
            _set_frame(scene, source_start + frame - start)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            evaluated = camera.evaluated_get(depsgraph)
            position, rotation, scale = evaluated.matrix_world.decompose()
            if last_rotation is not None:
                rotation.make_compatible(last_rotation)
            last_rotation = rotation.copy()
            positions.append(tuple(position))
            rotations.append(tuple(rotation))
            scales.append(tuple(scale))
            for path in values:
                value = _value(evaluated.data, path)
                if path == 'dof.focus_distance' and evaluated.data.dof.focus_object:
                    focus = evaluated.data.dof.focus_object.evaluated_get(depsgraph)
                    forward = -evaluated.matrix_world.col[2].to_3d().normalized()
                    value = abs((focus.matrix_world.translation - position).dot(forward))
                values[path].append(float(value))
        transform = curves(obj, name + ' motion')
        for path, samples in (('location', positions), ('rotation_quaternion', rotations), ('scale', scales)):
            transform.add(path, frames, samples)
        data = curves(obj.data, name + ' lens')
        for path, samples in values.items():
            data.add(path, frames, samples, interpolation='CONSTANT' if path in ('dof.use_dof', 'dof.aperture_blades') else 'LINEAR')
        return obj
    finally:
        _set_frame(scene, old_frame)
        scene.camera = old_camera
        if window and previous is not None:
            window.scene = previous


def create_cameras(master, curves=None, progress=None):
    """Create a camera per forward scene strip, including trimmed source timing."""
    import bpy
    report = {'cameras': [], 'missing_shot_cameras': [], 'uses_native_camera_markers': True}
    if master.sequence_editor is None:
        return report
    shots = sorted((s for s in master.sequence_editor.strips if s.type == 'SCENE'),
                   key=lambda s: (s.frame_final_start, s.channel))
    collection = None
    original_frame = master.frame_current + master.frame_subframe
    for strip in shots:
        scene = strip.scene
        camera = (strip.scene_camera or scene.camera) if scene else None
        if camera is None:
            report['missing_shot_cameras'].append(strip.name)
            continue
        if getattr(strip, 'speed_factor', 1) != 1 or getattr(strip, 'use_reverse_frames', False):
            raise ValueError('Master cameras require forward scene strips at their original speed')
        start, end = float(strip.frame_final_start), float(strip.frame_final_end)
        if end <= start:
            continue
        source_start = float(scene.frame_start + getattr(strip, 'animation_offset_start', 0)) + start - strip.frame_start
        if collection is None:
            collection = bpy.data.collections.new('SFM Master Cameras')
            master.collection.children.link(collection)
        name = strip.name + ' / Master Camera'
        native = (not camera.data.dof.focus_object and not _complex_animation(camera.data)
                  and all(not obj.constraints and obj.parent_type == 'OBJECT'
                          and obj.type in ('EMPTY', 'CAMERA') and not _complex_animation(obj)
                          for obj in _chain(camera)))
        if progress:
            progress('Building master camera for ' + strip.name)
        if native:
            proxy = _retimed_camera(camera, collection, name, start, end, source_start)
            method = 'shared_actions_retimed_with_native_nla'
        else:
            proxy = _baked_camera(camera, scene, collection, name, start, end, source_start, curves)
            method = 'evaluated_camera_baked_at_each_output_frame'
        proxy['sfm_master_camera_proxy'] = True
        proxy['sfm_source_shot'] = scene.name
        proxy['sfm_source_camera'] = camera.name
        marker = next((m for m in master.timeline_markers if m.name == strip.name and m.frame == round(start)), None)
        if marker is None:
            marker = master.timeline_markers.new(strip.name, frame=round(start))
        marker.camera = proxy
        report['cameras'].append({'shot': strip.name, 'source_scene': scene.name,
                                  'source_camera': camera.name, 'master_camera': proxy.name,
                                  'master_start': start, 'master_end_exclusive': end,
                                  'source_start': source_start, 'method': method})
    if report['cameras']:
        master.camera = bpy.data.objects[report['cameras'][0]['master_camera']]
        _set_frame(master, original_frame)
    return report


def assign_camera(master):
    """Compatibility entry point for existing repair scripts."""
    create_cameras(master)
    return master.camera

