"""World-plane sprite corners decoded from PET's type-2 vertex helper.

Source renderer/tick parity remains unverified.
"""
import math

def validate(renderer,function):
    value=float(renderer.get('orientation_type',0))
    if not math.isfinite(value) or value not in (0,1,2):
        raise ValueError('Non-camera-facing sprite orientation is unsupported')
    if value in (1,2):
        if function!='render_animated_sprites':
            raise ValueError('Non-camera-facing orientation requires animated sprites')
        cp=control_point(renderer)
        if value==1 and cp!=-1:
            raise ValueError('Upright sprite orientation control points are unverified')
    return int(value)

def control_point(renderer):
    cp=float(renderer.get('orientation control point',-1))
    if not math.isfinite(cp) or cp!=int(cp) or not -1<=cp<64:
        raise ValueError('Invalid sprite orientation control point')
    return int(cp)

def world_plane_yaw(yaw,orientation,renderer_function,orientation_control_point=-1,*,spritecard=False):
    """Historical entry point: yaw is independent of roll, never added to it.

    SpriteCard modes 0..2 have decoded shader math. The installed CPU upright
    and world-plane helpers ignore yaw; CPU camera-facing yaw is unverified.
    """
    if (renderer_function!='render_animated_sprites'
            or orientation not in ((0,1,2) if spritecard else (1,2))):
        raise ValueError('Rotation Yaw Random requires verified animated-sprite geometry')
    if not isinstance(yaw,dict):raise ValueError('Invalid Rotation Yaw Random parameters')
    from particle_yaw import parameters
    return parameters(yaw['parameters'])

def sample_world_plane_yaw(parameters,rng):
    from particle_yaw import random_angle
    return random_angle(parameters,rng)

def upright_normal(camera_position):
    values=tuple(float(v) for v in camera_position)
    if len(values)!=3 or not all(math.isfinite(v) for v in values):
        raise ValueError('Invalid upright sprite camera position')
    length=math.hypot(values[0],values[1])
    if length<=1e-12:
        raise ValueError('Upright sprite camera axis is degenerate')
    return (values[0]/length,values[1]/length,0.)

def upright_corners(center,radius,angle,camera_position):
    """PET mode-1 vertex writes: horizontal camera perpendicular and world Z.

    Camera-interface identity and Source visual parity remain unverified.
    Degenerate camera axes fail explicitly rather than inventing an orientation.
    """
    center=tuple(float(v) for v in center)
    if len(center)!=3 or not all(math.isfinite(v) for v in center) or not math.isfinite(radius) or radius<0 or not math.isfinite(angle):
        raise ValueError('Invalid upright sprite geometry')
    nx,ny,_=upright_normal(camera_position)
    right=(-ny,nx,0.)
    c,s=math.cos(-angle),math.sin(-angle)
    return tuple(tuple(center[i]+radius*(a*right[i]+(b if i==2 else 0.)) for i in range(3))
                 for a,b in ((-c-s,s-c),(s-c,s+c),(s+c,c-s),(c-s,-c-s)))

def world_corners(center,radius,angle):
    center=tuple(float(v) for v in center)
    if len(center)!=3 or not all(math.isfinite(v) for v in center) or not math.isfinite(radius) or radius<0 or not math.isfinite(angle):
        raise ValueError('Invalid world-plane sprite geometry')
    c=math.cos(angle)*radius;s=math.sin(angle)*radius
    return tuple((center[0]+x,center[1]+y,center[2]) for x,y in
                 ((c+s,c-s),(c-s,-c-s),(-c-s,-c+s),(-c+s,c+s)))
