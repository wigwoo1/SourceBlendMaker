"""Map an active Source camera's shutter seconds to native Blender frame units."""
def apply(scene,shot,camera,frames,seconds,fps,Curves):
 qualities=[int(shot.value(camera,'motionBlurQuality',t,0)) for t in seconds]
 shutter=[max(0.,float(shot.value(camera,'shutterSpeed',t,.0208))*fps) for t in seconds]
 enabled=[quality>0 and duration>0 for quality,duration in zip(qualities,shutter)]
 curves=Curves(scene,scene.name+' camera render settings',reuse=True)
 scene.render.use_motion_blur=any(enabled)
 effective=[duration if active else 0. for duration,active in zip(shutter,enabled)]
 scene.render.motion_blur_shutter=effective[0]
 scene.render.motion_blur_position='CENTER'
 curves.add('render.motion_blur_shutter',frames,effective,'CONSTANT')
 return {'camera':camera.name,'enabled_frames':sum(enabled),'shutter_frames_minimum':min(shutter),
         'shutter_frames_maximum':max(shutter),'position':'CENTER','source_sampling_equivalence_verified':False}
