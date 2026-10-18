"""Experimental leaf-ambient interpolation; map/leaf selection is separate."""
import math
from particle_tint_lighting.point_light import f32

def interpolate(samples, center, half_size, point):
    if any(len(v)!=3 or any(not math.isfinite(x) for x in v)
           for v in (center,half_size,point)) or any(x<0 for x in half_size):
        raise ValueError('Finite leaf bounds and point required')
    cube=[[0.]*3 for _ in range(6)];weight_sum=f32(0.)
    for raw in samples:
        if len(raw)!=28:raise ValueError('Ambient sample must contain 28 bytes')
        positions=[]
        for axis in range(3):
            base=f32(f32(center[axis])-f32(half_size[axis]))
            displacement=f32(f32(raw[24+axis])*f32(half_size[axis]))
            positions.append(f32(base+f32(displacement*f32(2./255.))))
        delta=[f32(positions[i]-f32(point[i])) for i in range(3)]
        squared=f32(f32(f32(delta[0]*delta[0])+f32(delta[1]*delta[1]))+f32(delta[2]*delta[2]))
        weight=f32(1./f32(squared+1.));weight_sum=f32(weight_sum+weight)
        for face in range(6):
            exponent=raw[face*4+3];exponent=exponent-256 if exponent>=128 else exponent
            scale=f32(math.ldexp(1.,exponent)/255.)
            for channel in range(3):
                value=f32(f32(f32(raw[face*4+channel])*scale)*f32(255.))
                cube[face][channel]=f32(cube[face][channel]+f32(value*weight))
    if not samples:return cube
    inverse=f32(1./weight_sum)
    return [[f32(value*inverse) for value in face] for face in cube]
