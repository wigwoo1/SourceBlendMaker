"""Native sequencer workspace for continuous playback of the imported edit."""
def prepare(master):
    import bpy
    from pathlib import Path
    workspace=bpy.data.workspaces.get('SFM Timeline')
    if workspace is None:
        template=Path(bpy.utils.system_resource('SCRIPTS'))/'startup/bl_app_templates_system/Video_Editing/startup.blend'
        with bpy.data.libraries.load(str(template),link=False) as (source,target):
            target.workspaces=[name for name in source.workspaces if name=='Video Editing']
        workspace=next((w for w in target.workspaces if w is not None),None)
    if workspace is None:raise ValueError('Video Editing workspace template is unavailable')
    workspace.name='SFM Timeline'
    workspace.sequencer_scene=master
    workspace.use_scene_time_sync=False
    workspace.use_pin_scene=True
    previous_windows=[(window,window.workspace,window.scene) for window in bpy.context.window_manager.windows]
    for window,_,_ in previous_windows:
        window.workspace=workspace;window.scene=master
    for screen in workspace.screens:
        for area in screen.areas:
            if area.type!='SEQUENCE_EDITOR':continue
            space=area.spaces.active
            space.display_mode='IMAGE'
            space.show_region_ui=False
    for window,previous,scene in previous_windows:
        window.workspace=previous;window.scene=scene
    master['sfm_timeline_workspace']=workspace.name
    return workspace
