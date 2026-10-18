"""Save an immediately inspectable shot while retaining the master render timeline."""

def prepare_open_state(master,shots):
    import bpy
    candidates=[scene for scene in shots if scene.camera and len(scene.objects)]
    if not candidates:raise ValueError('No populated camera shot available for opening')
    from timeline_workspace import prepare
    workspace=prepare(master)
    master['sfm_opening_shot']=candidates[0].name
    for shot in candidates:shot['sfm_master_timeline']=master.name
    scene=candidates[0];scene.frame_set(scene.frame_start)
    for window in bpy.context.window_manager.windows:
        window.scene=scene
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_perspective='CAMERA'
                space.camera=scene.camera;space.clip_end=max(space.clip_end,10000)
                space.shading.type='SOLID'
                space.overlay.show_overlays=False
    return scene

