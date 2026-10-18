"""Source Refract displacement math; not yet a connected Blender material.

Reference: ValveSoftware/source-sdk-2013, refract_ps2x.fxc lines 106-114.
Inputs are decoded normal XY (signed), linear alpha, and normalized screen UV.
This deliberately excludes tint, blur, normal decoding and overlapping layers.
"""
import math

def dx9_blur_amount(authored):
    """Valve SDK DX9 MAXBLUR=1 clamp; SFM branch parity is unverified."""
    if isinstance(authored,bool) or not isinstance(authored,int):
        raise ValueError('Refraction blur must be an integer')
    return min(1,max(0,authored))

def blur_samples(amount):
    """Source shader screen-UV offsets and weights, before color conversion.

    BLUR=1 uses four bilinear samples for a three-by-three box kernel.
    Larger authored values use the shader's square uniform kernel.
    """
    if isinstance(amount,bool) or not isinstance(amount,int) or not 0<=amount<=2:
        raise ValueError('Supported refraction blur amounts are 0, 1 and 2')
    if amount==0:return ((0.,0.,1.),)
    fraction=1/512
    if amount==1:
        return ((-.5*fraction,-.5*fraction,4/9),
                (fraction,-.5*fraction,2/9),
                (-.5*fraction,fraction,2/9),
                (fraction,fraction,1/9))
    weight=1/(2*amount+1)**2
    return tuple((x*fraction,y*fraction,weight)
                 for x in range(-amount,amount+1)
                 for y in range(-amount,amount+1))

def tint_factor(tint,coverage=1.,texture=None,vertex=None):
    """Single-layer tint with normal/vertex-alpha coverage, no blur or cubemap."""
    if len(tint)!=3 or not 0<=coverage<=1:raise ValueError('Invalid refraction tint')
    result=[float(v) for v in tint]
    for values,multiplier in ((texture,2.),(vertex,1.)):
        if values is not None:
            if len(values)!=3:raise ValueError('Invalid refraction tint channels')
            result=[a*float(b)*multiplier for a,b in zip(result,values)]
    if not all(math.isfinite(v) and v>=0 for v in result):raise ValueError('Invalid refraction tint values')
    return tuple(1+coverage*(v-1) for v in result)

def compositor_pixels(offset,width,height):
    """Blender 5.2 Displace pulls from opposite pixel offsets, not screen UVs."""
    if len(offset)!=2 or not all(math.isfinite(float(v)) for v in offset):
        raise ValueError('Invalid refraction displacement')
    if any(not math.isfinite(float(v)) or float(v)<=0 or int(v)!=v for v in (width,height)):
        raise ValueError('Invalid refraction image size')
    return -float(offset[0])*width,-float(offset[1])*height

def displacement(normal_xy,normal_alpha,amount,vertex_alpha=1.,vertex_modulate=False):
    if len(normal_xy)!=2:raise ValueError('Refraction requires two normal components')
    x,y=(float(v) for v in normal_xy)
    a,rate,vertex=(float(v) for v in (normal_alpha,amount,vertex_alpha))
    if not all(math.isfinite(v) for v in (x,y,a,rate,vertex)):
        raise ValueError('Invalid refraction parameters')
    if not 0<=a<=1 or not 0<=vertex<=1:
        raise ValueError('Invalid refraction alpha')
    scale=a*rate*(vertex if vertex_modulate else 1.)
    return x*scale,y*scale

def sampling_uv(uv,normal_xy,normal_alpha,amount,vertex_alpha=1.,vertex_modulate=False):
    if len(uv)!=2 or not all(math.isfinite(float(v)) for v in uv):
        raise ValueError('Invalid screen coordinates')
    dx,dy=displacement(normal_xy,normal_alpha,amount,vertex_alpha,vertex_modulate)
    return float(uv[0])+dx,float(uv[1])+dy
