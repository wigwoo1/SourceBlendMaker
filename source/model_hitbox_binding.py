"""Bind parsed bone-local hitboxes to a currently evaluated imported armature.

This supplies geometry, not Source's hitbox selection/random sampling policy.
The caller must evaluate the scene at the requested particle time first.
"""
import itertools,math

class Binding:
    def __init__(self,armature,mdl,hitboxes,*,set_name='default',scale=.0254):
        if armature.type!='ARMATURE':raise ValueError('Hitboxes require an imported armature')
        if not math.isfinite(scale) or scale<=0:raise ValueError('Positive finite Source scale required')
        matches=[s for s in hitboxes['sets'] if s['name']==set_name]
        if len(matches)!=1:raise ValueError('Unique authored hitbox set required')
        if len(mdl.bones)!=hitboxes['bone_count']:raise ValueError('Hitbox and model bone counts differ')
        self.armature=armature;self.boxes=matches[0]['boxes'];self.scale=scale
        self.names=[mdl.bones[b['bone']].name[:63] for b in self.boxes]
        if any(armature.pose.bones.get(n) is None for n in self.names):raise ValueError('Hitbox bone missing from imported armature')
    def point(self,index,relative,depsgraph,*,hitbox_scale=1.,allow_extrapolation=False):
        """Resolve a persisted hitbox index and normalized box-local coordinate.

        Selection, random distribution and Source temporal interpolation are
        caller policies. Scaling acts around the local box center.
        The Source model-placement endpoint scale is applied by selection,
        separately from this generic center-scaling argument. Explicit
        allow_extrapolation permits Source's persisted coordinates outside
        [0,1]; the default remains strict for ordinary geometry callers.
        """
        from mathutils import Vector
        if type(index) is not int or not 0<=index<len(self.boxes):raise ValueError('Particle hitbox index outside selected set')
        relative=tuple(relative)
        if type(allow_extrapolation) is not bool:raise ValueError('Explicit hitbox extrapolation policy required')
        if len(relative)!=3 or not all(math.isfinite(v) and (allow_extrapolation or 0<=v<=1) for v in relative):raise ValueError('Finite normalized hitbox coordinates required')
        if not math.isfinite(hitbox_scale) or hitbox_scale<0:raise ValueError('Finite nonnegative hitbox scale required')
        box=self.boxes[index]
        local=[(a+b)*.5+(a+(b-a)*r-(a+b)*.5)*hitbox_scale for a,b,r in zip(box['minimum'],box['maximum'],relative)]
        evaluated=self.armature.evaluated_get(depsgraph)
        matrix=evaluated.matrix_world@evaluated.pose.bones[self.names[index]].matrix
        point=tuple(matrix@(Vector(local)*self.scale))
        if not all(math.isfinite(v) for v in point):raise ValueError('Nonfinite animated hitbox point')
        return point
    def corners(self,depsgraph):
        from mathutils import Vector
        evaluated=self.armature.evaluated_get(depsgraph);rows=[]
        for box,name in zip(self.boxes,self.names):
            matrix=evaluated.matrix_world@evaluated.pose.bones[name].matrix
            points=[tuple(matrix@(Vector(p)*self.scale)) for p in itertools.product(*zip(box['minimum'],box['maximum']))]
            if not all(math.isfinite(v) for p in points for v in p):raise ValueError('Nonfinite animated hitbox geometry')
            rows.append(dict(bone=name,group=box['group'],name=box['name'],corners=points))
        return rows
