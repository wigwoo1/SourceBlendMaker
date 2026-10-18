"""Validate the stationary-control assumption of maintained particle geometry."""
import math

def lock_settings(parameters):
    index=float(parameters.get('control_point_number',0))
    if not math.isfinite(index) or index!=int(index) or not 0<=index<64:
        raise ValueError('Invalid particle lock control point')
    if float(parameters.get('distance fade range',0))!=0 or any(float(parameters.get(k,1))!=1 for k in ('start_fadeout_min','start_fadeout_max','end_fadeout_min','end_fadeout_max')):
        raise ValueError('Partial control-point locks are unsupported')
    return int(index),bool(parameters.get('lock rotation',False))

def stationary_origin(scene,control,frames,tolerance=1e-5):
    """Check all supplied times and midpoints, restoring the caller's frame."""
    times=sorted(set(float(f) for f in frames))
    if not times:raise ValueError('Particle control check requires sample frames')
    times=sorted(set(times+[(a+b)*.5 for a,b in zip(times,times[1:])]))
    old_frame,old_subframe=scene.frame_current,scene.frame_subframe
    origin=None
    try:
        for time in times:
            frame=math.floor(time);scene.frame_set(frame,subframe=time-frame)
            position=control.matrix_world.translation.copy()
            if origin is None:origin=position
            elif (position-origin).length>tolerance:
                raise ValueError(f'Moving maintained-sprite control point {control.name} at frame {time:g} is not yet supported')
        return origin
    finally:scene.frame_set(old_frame,subframe=old_subframe)
