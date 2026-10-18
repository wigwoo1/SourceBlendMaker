"""Scalar port of the statically inspected installed SFM noise helper.

Noise math only: does not claim engine emission tick or random stream parity.
"""
import math,struct

def f32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]

def coordinate(value):
    if not math.isfinite(value):
        raise ValueError('Noise coordinate must be finite')
    try:shifted=f32(f32(value)+32768.)
    except OverflowError:raise ValueError('Noise coordinate exceeds float32 range') from None
    bits=struct.unpack('<I',struct.pack('<f',shifted))[0]&65535
    return bits>>8,(bits&255)/256.

def noise(point,tables):
    px,py,pz,values=tables
    coords=[coordinate(v) for v in point]
    (x,fx),(y,fy),(z,fz)=coords
    def corner(dx,dy,dz):
        return values[pz[(py[(px[(x+dx)&255]+y+dy)&255]+z+dz)&255]]
    def lerp(a,b,t):
        return f32(a+f32(f32(b-a)*t))
    near=lerp(lerp(corner(0,0,0),corner(1,0,0),fx),
              lerp(corner(0,1,0),corner(1,1,0),fx),fy)
    far=lerp(lerp(corner(0,0,1),corner(1,0,1),fx),
             lerp(corner(0,1,1),corner(1,1,1),fx),fy)
    return f32(f32(lerp(near,far,fz)-.5)*2.)
