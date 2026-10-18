"""Conservative checks for control objects whose world transforms are static."""

_TRANSFORM_PATHS={
    'location','rotation_euler','rotation_quaternion','rotation_axis_angle','scale',
    'delta_location','delta_rotation_euler','delta_rotation_quaternion','delta_scale',
}


def _action_curves(action,animation_data):
    if action is None:return []
    if hasattr(action,'fcurves'):
        return list(action.fcurves)
    curves=[]
    slots=getattr(action,'slots',())
    assigned=getattr(animation_data,'action_slot',None)
    if assigned is not None:slots=(assigned,)
    for layer in getattr(action,'layers',()):
        for strip in getattr(layer,'strips',()):
            for slot in slots:
                try:bag=strip.channelbag(slot)
                except (AttributeError,TypeError,RuntimeError):return None
                if bag is not None:curves.extend(getattr(bag,'fcurves',()))
    return curves


def _constant_curve(curve):
    if getattr(curve,'data_path',None) not in _TRANSFORM_PATHS:return False
    if len(getattr(curve,'modifiers',())):return False
    points=list(getattr(curve,'keyframe_points',()))
    if not points:
        points=list(getattr(curve,'sampled_points',()))
    if not points:return False
    values=[float(point.co.y) for point in points]
    return all(value==values[0] for value in values[1:])


def transform_is_static(obj):
    """Return true only when every object ancestor has constant transforms.

    Any constraint, driver, NLA strip, unknown animated property, or
    non-object parenting makes the check fail closed. This intentionally
    favors the exact sampling path when Blender cannot prove the transform is
    constant.
    """
    current=obj;visited=set()
    while current is not None:
        if getattr(current,'sfm_time_dependent',False):return False
        identity=id(current)
        if identity in visited:return False
        visited.add(identity)
        if getattr(current,'constraints',()):return False
        if getattr(current,'rigid_body',None) is not None:return False
        if getattr(current,'parent',None) is not None and getattr(current,'parent_type','OBJECT')!='OBJECT':return False
        animation_data=getattr(current,'animation_data',None)
        if animation_data is not None:
            if getattr(animation_data,'drivers',()) or getattr(animation_data,'nla_tracks',()):return False
            action=getattr(animation_data,'action',None)
            curves=_action_curves(action,animation_data)
            if curves is None or any(not _constant_curve(curve) for curve in curves):return False
        current=getattr(current,'parent',None)
    return True


def controls_are_static(control_objects):
    return all(transform_is_static(obj) for obj in control_objects.values())
