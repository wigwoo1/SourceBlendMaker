"""Sphere-point arithmetic from installed initializer 0x102045c0.

Source maintains mutable
angle/height counters; this helper uses algebraic values and Python trig.
"""
import math

def validate(parameters):
    from particle_epitrochoid import validate as validate_shared
    validate_shared({k:v for k,v in parameters.items() if k.startswith('operator ')})
    cp=float(parameters.get('control point number',0))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64:
        raise ValueError('Invalid spiral sphere control point')
    if any(float(parameters.get(k,0))!=0 for k in ('min initial speed','max initial speed')):
        raise ValueError('Spiral sphere initial speed is unverified')
    offset(0,parameters)
    return int(cp)

def offset(counter,parameters):
    if isinstance(counter,bool) or not isinstance(counter,int) or counter<0:
        raise ValueError('Invalid spiral sphere counter')
    if parameters.get('Use Particle Count as Density Scale',False):
        raise ValueError('Spiral sphere batch-count density is unverified')
    if float(parameters.get('Override CP (X/Y/Z *= Radius/Density/Speed)',-1))!=-1:
        raise ValueError('Spiral sphere control-point scaling is unverified')
    density=float(parameters.get('density',0));radius=float(parameters.get('initial radius',0))
    if not math.isfinite(density) or density!=int(density) or density<0 or not math.isfinite(radius):
        raise ValueError('Invalid spiral sphere density/radius')
    # The installed loop resets when count > density (not count >= density).
    phase_index=counter%(int(density)+1)
    step=2/max(1,density)
    z=1-step*.5-phase_index*step
    angle=phase_index*(3-math.sqrt(5))*math.pi
    planar=math.sqrt(max(0,1-z*z))
    return (radius*math.cos(angle)*planar,radius*math.sin(angle)*planar,radius*z)
