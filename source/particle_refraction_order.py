"""Experimental camera-depth ordering; exact Source sorting remains unverified."""
import math

def back_to_front(centers,camera_position,camera_forward):
    """Return stable indices by decreasing signed camera-axis depth.

    This explicitly uses view depth, not radial distance. Equal depths retain
    input order. All positions must share the same coordinate space.
    """
    def vector(value):
        if len(value)!=3:raise ValueError('Expected three coordinates')
        result=tuple(float(v) for v in value)
        if not all(math.isfinite(v) for v in result):raise ValueError('Nonfinite coordinates')
        return result
    camera=vector(camera_position);forward=vector(camera_forward)
    length=math.sqrt(sum(v*v for v in forward))
    if length==0:raise ValueError('Camera forward cannot be zero')
    forward=tuple(v/length for v in forward)
    depths=[sum((v-c)*f for v,c,f in zip(vector(center),camera,forward)) for center in centers]
    return sorted(range(len(depths)),key=lambda index:-depths[index])
