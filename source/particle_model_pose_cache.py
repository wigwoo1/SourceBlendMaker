"""Share evaluated model matrices across particles at the same shot time.

Time keys match Blender's integer frame and float32 subframe; this cache
introduces no coarser simulation grid or pose interpolation. Native scene
evaluation runs on cache misses, and the caller restores its rendering frame.
"""
import math

class PoseCache:
    def __init__(self,scene,shot,fps):
        self.scene=scene;self.shot=shot;self.fps=fps;self.poses={};self.evaluations=0
    def point(self,binding,index,relative,time):
        import bpy
        from mathutils import Vector
        if not math.isfinite(time):raise ValueError('Finite hitbox pose time required')
        from particle_target_time import cache_key
        key=cache_key(binding.armature.name,time,self.shot.start,self.fps)
        if key not in self.poses:
            frame=1+(time-self.shot.start)*self.fps
            self.scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
            evaluated=binding.armature.evaluated_get(bpy.context.evaluated_depsgraph_get())
            self.poses[key]={bone.name:(evaluated.matrix_world@bone.matrix).copy() for bone in evaluated.pose.bones}
            self.evaluations+=1
        box=binding.boxes[index]
        local=Vector(tuple((a+(b-a)*r)*binding.scale for a,b,r in zip(box['minimum'],box['maximum'],relative)))
        point=tuple(self.poses[key][binding.names[index]]@local)
        if not all(math.isfinite(v) for v in point):raise ValueError('Nonfinite cached hitbox point')
        return point
