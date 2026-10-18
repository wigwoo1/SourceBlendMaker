"""Experimental bridge from parent simulation snapshots to Blender CP views."""
from particle_child_cp import History


def validate_source(definition,births):
    # Repeated births can read back an earlier CP write into their own spawn
    # location. That requires chronological parent integration, not a second
    # post-bake pass. Do not silently bake those effects at the original CP.
    if len({birth.simulation_time for birth in births})>1:
        raise ValueError('Child-control-point feedback across repeated birth times requires chronological integration')
    for module in definition['modules'].get('operators',[]):
        if not module.get('parameters',{}).get('operator enabled',True):continue
        if 'control point' in module['function'].lower():
            raise ValueError('Child-control-point writes combined with other CP operators require chronological integration')
    if any(module.get('parameters',{}).get('operator enabled',True)
           and module['function']!='random force' for module in definition['modules'].get('forces',[])):
        raise ValueError('Child-control-point writes with CP-dependent forces require chronological integration')


class ControlPointView:
    sfm_time_dependent=True

    def __init__(self,name,base,history,index,scene,shot_start,fps,scale,set_time):
        self.name=name;self.parent=base;self.history=history;self.index=index
        self.scene=scene;self.shot_start=shot_start;self.fps=fps;self.scale=scale
        self.set_time=set_time

    @property
    def matrix_world(self):
        from mathutils import Vector
        from particle_sim import simulation_at
        time=self.shot_start+(self.scene.frame_current+self.scene.frame_subframe-1)/self.fps
        clock=simulation_at(self.history.segments,time)
        try:position=self.history.query(max(0.,clock)).get(self.index)
        finally:self.set_time(time)
        base=self.parent.evaluated_get(self.scene.view_layers[0].depsgraph).matrix_world.copy()
        if position is not None:base.translation=Vector(position)*self.scale
        return base

    def evaluated_get(self,_depsgraph):return self


def overlay(context,config,descriptor,controls,scene,shot_start,fps,scale,set_time):
    points=list(descriptor['control_points'])
    if not points:raise ValueError('Child-control-point writes require a system origin')
    result=dict(controls);origin_id=points[0]['id'];origin=result.get(origin_id)
    if origin is None:raise ValueError('Child-control-point origin transform is missing')
    history=getattr(context,'child_cp_history',None)
    if history is None:
        history=History(config,context.snapshot)
        history.segments=context.segments
        context.child_cp_history=history
    # The supported source births occur together, so this is the maximum
    # writable active prefix. Unwritten CPs must not inflate the highest used
    # CP index for child distributions or future emission scaling.
    count=min(config['count'],max(0,len(context.births)-config['first_particle']))
    for index in range(config['first_control_point'],config['first_control_point']+count):
        while len(points)<=index:
            n=len(points)
            points.append({'id':f'{origin_id}:child-cp:{n}','name':f'controlPoint{n}',
                'type':'DmeTransform','generated_by':'parent particle position'})
        identity=points[index]['id'];base=result.get(identity,origin)
        result[identity]=ControlPointView(f'parent {context.instance_id} CP{index}',base,history,index,
                                        scene,shot_start,fps,scale,set_time)
    return points,result
