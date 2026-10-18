"""Scalar distribution from Valve CParticleCollection::RandomFloatExp.

https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/particles/particles.h
The random stream itself is supplied by the converter, not Source's table.
"""
import math

def color_bytes(initializers,base_color,rng):
    """Untinted Color Random uses one common RGB blend factor."""
    if 'Color Random' not in initializers:return list(base_color[:3])
    parameters=initializers['Color Random']
    if float(parameters.get('tint_perc',0))!=0:
        raise ValueError('Control-point particle tint is unsupported')
    low=parameters.get('color1',[255]*4)[:3]
    high=parameters.get('color2',[255]*4)[:3]
    if len(low)!=3 or len(high)!=3:raise ValueError('Three color channels required')
    if any(not math.isfinite(float(v)) or not 0<=float(v)<=255 for v in list(low)+list(high)):
        raise ValueError('Finite color byte channels required')
    fraction=rng.random()
    return [float(a)+(float(b)-float(a))*fraction for a,b in zip(low,high)]

def alpha_bounds(initializers, base_alpha):
    """Alpha Random defaults to 255; absent initializer uses definition alpha."""
    if 'Alpha Random' not in initializers:
        return base_alpha,base_alpha
    parameters=initializers['Alpha Random']
    return parameters.get('alpha_min',255),parameters.get('alpha_max',255)

def rotation_angle(initializers,rng):
    """Installed Rotation Random defaults; converter RNG remains approximate."""
    if 'Rotation Random' not in initializers:return 0.
    parameters=initializers['Rotation Random']
    angle=math.radians(float(parameters.get('rotation_initial',0))+
                       random_float_exp(rng,parameters.get('rotation_offset_min',0),
                                        parameters.get('rotation_offset_max',360),
                                        parameters.get('rotation_random_exponent',1)))
    if parameters.get('randomly_flip_direction',True) and rng.random()<.5:
        angle=-angle
    if not math.isfinite(angle):raise ValueError('Invalid particle rotation angle')
    return angle

def random_float_exp(rng,minimum,maximum,exponent=1):
    minimum,maximum,exponent=map(float,(minimum,maximum,exponent))
    if not all(math.isfinite(v) for v in (minimum,maximum,exponent)) or exponent<=0:
        raise ValueError('Particle distribution requires finite bounds and positive exponent')
    if exponent==1:return rng.uniform(minimum,maximum)
    return minimum+(maximum-minimum)*rng.random()**exponent

def birth_ranges(config,rng):
    def value(name):
        bounds=config[name+'_range'];exponent=config.get(name+'_exponent',1)
        return bounds[0] if bounds[0]==bounds[1] else random_float_exp(rng,*bounds,exponent)
    lifetime=value('lifetime') if not config.get('ordered_lifetime_samples') else None
    for sample in config.get('ordered_lifetime_samples') or []:
        # Earlier writes still consume random samples; the last write wins.
        lifetime=random_float_exp(rng,*sample['bounds'],sample['exponent'])
    return lifetime,value('radius')
