import sys
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
sys.path.insert(0,str(APP/'vendor'))

import bpy
import numpy as np
from blender_worker import AnimationCurves,Curves

Curves.configure_animation_sampling(60,30)
scene=bpy.context.scene
owner=bpy.data.objects.new('sampled motion',None)
scene.collection.objects.link(owner)
frames=np.arange(1,62,dtype=np.float32)
values=np.column_stack((frames-1,(frames-1)*2,(frames-1)*3))
AnimationCurves(owner,'sampled motion').add('location',frames,values)
action=owner.animation_data.action
bag=action.layers[0].strips[0].channelbags[0]
location=bag.fcurves.find('location',index=0)
assert len(location.keyframe_points)==31,len(location.keyframe_points)
assert location.keyframe_points[0].co.x==1
assert location.keyframe_points[-1].co.x==61
assert all(abs(p.co.x-round(p.co.x))<1e-6 for p in location.keyframe_points)
scene.frame_set(2)
evaluated=owner.evaluated_get(bpy.context.evaluated_depsgraph_get())
assert abs(evaluated.location.x-1)<1e-5,evaluated.location.x

full=bpy.data.objects.new('full-rate motion',None)
scene.collection.objects.link(full)
Curves(full,'full-rate motion').add('location',frames,values)
full_bag=full.animation_data.action.layers[0].strips[0].channelbags[0]
assert len(full_bag.fcurves.find('location',index=0).keyframe_points)==61

constant=bpy.data.objects.new('constant motion',None)
scene.collection.objects.link(constant)
AnimationCurves(constant,'constant motion').add('location',frames,values,interpolation='CONSTANT')
constant_bag=constant.animation_data.action.layers[0].strips[0].channelbags[0]
assert len(constant_bag.fcurves.find('location',index=0).keyframe_points)==61

print('BLENDER_ANIMATION_SAMPLING_PASS',Curves.animation_sampling_report())
