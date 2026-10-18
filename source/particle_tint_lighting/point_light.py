"""Experimental engine color reduction; obtaining six lighting inputs is separate.

Reproduces the inspected scalar float32 sum/mean and byte conversion for
finite, nonnegative inputs. Does not implement map sampling or Source RNG.
"""
import math
import struct

def f32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]

def color_bytes(cube, active=True):
    if not active:
        return (255,255,255,255)
    if len(cube)!=6 or any(len(face)!=3 for face in cube):
        raise ValueError('Six RGB directional lighting values required')
    if any(not math.isfinite(v) or v<0 for face in cube for v in face):
        raise ValueError('Lighting inputs must be finite and nonnegative')
    result=[]
    for channel in range(3):
        total=f32(0.)
        for face in cube:
            total=f32(total+f32(face[channel]))
        mean=min(1.,f32(total*f32(1./6.)))
        result.append(int(f32(mean*f32(255.))))
    return (*result,0)
