"""Installed ordinary CP burst-count arithmetic; scene clock binding pending.

Snapshot object count overrides are deliberately excluded. Source samples the
CP at authored start when crossed by the previous-call interval, otherwise at
current CP state. Production emitter integration must supply that sample.
"""
import math,struct
def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
def settings(parameters):
    cp=parameters.get('emission count scale control point',-1)
    field=parameters.get('emission count scale control point field',0)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v!=int(v) for v in (cp,field)):
        raise ValueError('Integer burst scaling CP and component required')
    if cp<0 or not 0<=field<=2:raise ValueError('Invalid burst scaling CP/component')
    if parameters.get('control point with snapshot data',-1)!=-1:
        raise ValueError('Snapshot burst count override remains unsupported')
    return int(cp),int(field)
def count(selected,component):
    if type(selected) is not int or not math.isfinite(component):raise ValueError('Invalid burst count sample')
    product=f32(f32(selected)*f32(component))
    if not math.isfinite(product) or not -2147483648<=product<2147483648:
        raise ValueError('Burst scaling outside signed conversion range')
    return max(0,math.trunc(product))
def sample_time(current,previous_dt,start,delay=0.):
    current,previous_dt,start,delay=map(f32,(current,previous_dt,start,delay))
    if not all(math.isfinite(v) for v in (current,previous_dt,start,delay)) or previous_dt<0:
        raise ValueError('Invalid burst sampling interval')
    authored=f32(start+delay)
    return authored if f32(current-previous_dt)<=authored<=current else None
