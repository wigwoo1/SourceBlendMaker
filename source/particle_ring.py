"""Zero-thickness ring initializer for sprites and experimental spline ropes.

Source random ordering, counter resets and live appearance remain unverified.
"""
import math

def settings(parameters):
    """Installed ring unpack defaults, without mutating authored parameters."""
    result={'run for killed parent particles':True,'control point number':0,
            'initial radius':0.,'thickness':0.,'min initial speed':0.,'max initial speed':0.,
            'pitch':0.,'yaw':0.,'roll':0.,'even distribution':False,
            'even distribution count':-1,'XY velocity only':True,
            'Override CP (X/Y/Z *= Radius/Thickness/Speed)':-1,
            'Override CP 2 (X/Y/Z *= Pitch/Yaw/Roll)':-1,**parameters}
    numeric=('initial radius','thickness','min initial speed','max initial speed','pitch','yaw','roll','even distribution count')
    if not all(math.isfinite(float(result[key])) for key in numeric):
        raise ValueError('Nonfinite ring parameters')
    if float(result['thickness'])<0 or float(result['min initial speed'])>float(result['max initial speed']):
        raise ValueError('Invalid ring thickness or speed range')
    for key in ('control point number','Override CP (X/Y/Z *= Radius/Thickness/Speed)','Override CP 2 (X/Y/Z *= Pitch/Yaw/Roll)'):
        value=float(result[key]);minimum=0 if key=='control point number' else -1
        if not math.isfinite(value) or value!=int(value) or not minimum<=value<64:
            raise ValueError('Invalid ring control point')
    return result

def angle_matrix(pitch,yaw,roll):
    """Source QAngle convention: yaw, then pitch, then roll, in degrees.

    Formula reference: Valve source-sdk-2013 mathlib/mathlib_base.cpp AngleMatrix.
    """
    angles=tuple(map(float,(pitch,yaw,roll)))
    if not all(math.isfinite(v) for v in angles):raise ValueError('Invalid ring angles')
    p,y,r=map(math.radians,angles)
    sp,cp=math.sin(p),math.cos(p);sy,cy=math.sin(y),math.cos(y);sr,cr=math.sin(r),math.cos(r)
    return ((cp*cy,sp*sr*cy-cr*sy,sp*cr*cy+sr*sy),
            (cp*sy,sp*sr*sy+cr*cy,sp*cr*sy-sr*cy),
            (-sp,sr*cp,cr*cp))

def rotate(matrix,vector):
    if len(matrix)!=3 or any(len(row)!=3 for row in matrix) or len(vector)!=3:
        raise ValueError('Invalid ring transform shape')
    values=[float(v) for row in matrix for v in row]+list(map(float,vector))
    if not all(math.isfinite(v) for v in values):raise ValueError('Invalid ring transform values')
    return tuple(sum(float(row[i])*float(vector[i]) for i in range(3)) for row in matrix)

def transformed_sample(counter,parameters,batch_count,speed,control_rotation,control_origin,random_fraction=None):
    """Prototype zero-thickness ring with explicit rotation and CP transform."""
    parameters=settings(parameters)
    identity_parameters=dict(parameters,pitch=0,yaw=0,roll=0)
    if parameters['even distribution']:
        point,_=identity_sample(counter,identity_parameters,batch_count,speed)
    else:
        if float(parameters['thickness'])!=0 or any(parameters[key]>=0 for key in ('Override CP (X/Y/Z *= Radius/Thickness/Speed)','Override CP 2 (X/Y/Z *= Pitch/Yaw/Roll)')):
            raise ValueError('Random ring thickness or override control points are unsupported')
        if random_fraction is None or not math.isfinite(float(random_fraction)) or not 0<=float(random_fraction)<=1:
            raise ValueError('Random ring requires a finite random fraction in [0,1]')
        if isinstance(counter,bool) or not isinstance(counter,int) or counter<0:raise ValueError('Invalid ring context counter')
        # Installed initializer 0x102038c0 increments the counter, then
        # multiplies it by a fresh random 0..2pi step before fsincos.
        angle=(counter+1)*float(random_fraction)*math.tau
        radius=float(parameters['initial radius'])
        point=(radius*math.cos(angle),radius*math.sin(angle),0.)
    ring_rotation=angle_matrix(*(parameters.get(key,0) for key in ('pitch','yaw','roll')))
    offset=rotate(control_rotation,rotate(ring_rotation,point))
    origin=tuple(map(float,control_origin))
    if len(origin)!=3 or not all(math.isfinite(v) for v in origin):raise ValueError('Invalid ring origin')
    position=tuple(a+b for a,b in zip(offset,origin));distance=math.hypot(*offset)
    velocity=tuple(v*float(speed)/distance for v in offset) if distance else (0.,0.,0.)
    if parameters.get('XY velocity only',True):velocity=(velocity[0],velocity[1],0.)
    return position,velocity

def even_angle(counter,distribution_count,batch_count):
    """Source increments its context counter before multiplying the ring step."""
    if isinstance(counter,bool) or not isinstance(counter,int) or counter<0:
        raise ValueError('Invalid ring context counter')
    count=float(distribution_count)
    if count==-1:count=float(batch_count)
    if not math.isfinite(count) or count<=0:raise ValueError('Invalid ring distribution count')
    return (counter+1)*math.tau/count

def identity_sample(counter,parameters,batch_count,speed):
    """Zero-thickness, unrotated, even ring under an identity CP transform."""
    if not parameters.get('even distribution',False):raise ValueError('Ring random angle is not implemented')
    if any(float(parameters.get(key,0))!=0 for key in ('thickness','pitch','yaw','roll')):
        raise ValueError('Ring thickness and rotation require transform-aware sampling')
    if any(int(parameters.get(key,-1))>=0 for key in ('Override CP (X/Y/Z *= Radius/Thickness/Speed)','Override CP 2 (X/Y/Z *= Pitch/Yaw/Roll)')):
        raise ValueError('Ring override control points require history-aware sampling')
    radius=float(parameters.get('initial radius',0));speed=float(speed)
    if not all(math.isfinite(v) for v in (radius,speed)):raise ValueError('Invalid ring radius or speed')
    angle=even_angle(counter,parameters.get('even distribution count',-1),batch_count)
    point=(radius*math.cos(angle),radius*math.sin(angle),0.)
    distance=math.hypot(*point)
    velocity=tuple(v*speed/distance for v in point) if distance else (0.,0.,0.)
    return point,velocity
