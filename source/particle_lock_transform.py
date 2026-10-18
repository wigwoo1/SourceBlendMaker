"""Shared rigid control-point lock transform for centers and trail history.

Inputs use the caller's vector/quaternion types and world-unit convention.
Partial locks use their separate displacement history and do not call this.
"""
import math


def bind_matrix_query(control,scene,time_at_age,shot_start,fps):
    """Read an evaluated control matrix at a requested authored scene time.

    time_at_age owns conversion from particle simulation age to scene seconds.
    Frame and subframe are restored even if evaluation fails.
    """
    if not math.isfinite(fps) or fps<=0:raise ValueError('Positive finite scene FPS required')
    def query(birth,age):
        time=float(time_at_age(birth,age))
        frame=1+(time-shot_start)*fps
        if not math.isfinite(frame):raise ValueError('Finite control sampling frame required')
        old_frame,old_subframe=scene.frame_current,scene.frame_subframe
        try:
            whole=math.floor(frame)
            scene.frame_set(whole,subframe=frame-whole)
            return control.evaluated_get(scene.view_layers[0].depsgraph).matrix_world.copy()
        finally:
            scene.frame_set(old_frame,subframe=old_subframe)
    return query


def center(position, current_matrix, birth_position, birth_rotation, rotate=False):
    if rotate:
        rotation=current_matrix.to_quaternion()@birth_rotation.inverted()
        return current_matrix.translation+rotation@(position-birth_position)
    return position+current_matrix.translation-birth_position


def bind_sampler(sampler,origins,birth_transforms,matrix_at_age,rotate=False,*,vector):
    """Add a full rigid lock to a birth motion sampler.

    matrix_at_age owns scene-clock mapping and frame restoration. Birth
    transforms and origins are captured here so later loop reassignment cannot
    substitute another effect's buffers. Partial locks require their own
    displacement history and must not use this wrapper.
    """
    origins={key:vector(value) for key,value in origins.items()}
    birth_transforms=dict(birth_transforms)
    def sample(birth,age,lifetime):
        offset,rgb,alpha,theta=sampler(birth,age,lifetime)
        origin=origins[birth.index]
        birth_position,birth_rotation=birth_transforms[birth.index]
        locked=center(origin+vector(offset),matrix_at_age(birth,age),birth_position,birth_rotation,rotate)
        return locked-origin,rgb,alpha,theta
    return sample


def bind_partial_sampler(sampler,control,scene,segments,fades,threshold,clock,shot_start,fps,scale,*,vector):
    """Retain the existing experimental translation-fade history per instance."""
    from particle_clock_inverse import real_time
    from particle_partial_lock import history_displacement
    query=bind_matrix_query(control,scene,lambda birth,time:time,shot_start,fps)
    fades=dict(fades)
    def position_at_time(time):
        return tuple(v/scale for v in query(None,time).translation)
    def sample(birth,age,lifetime):
        offset,rgb,alpha,theta=sampler(birth,age,lifetime)
        time=real_time(segments,birth.simulation_time+age,side='right',minimum_time=birth.time)
        received=history_displacement(segments,birth,time,lifetime,fades[birth.index],position_at_time,threshold,prepared_inverse=clock)
        return offset+vector(received)*scale,rgb,alpha,theta
    return sample
