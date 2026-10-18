"""Straight sequential path approximation; Source endpoint phase is unverified."""
import math

def validate(parameters):
    if parameters.get('bulge')!=0 or float(parameters.get('maximum distance',0))!=0:
        raise ValueError('Curved/jittered sequential particle paths are unsupported')
    if parameters.get('Save Offset',False):raise ValueError('Sequential path saved offsets are unsupported')
    count=float(parameters.get('particles to map from start to end',0))
    if not math.isfinite(count) or count<2 or count!=int(count):raise ValueError('Sequential path requires an explicit integer particle count of at least 2')
    start=int(parameters.get('start control point number',0));end=int(parameters.get('end control point number',1))
    if not 0<=start<64 or not 0<=end<64:raise ValueError('Invalid sequential path control point')
    return int(count),start,end

def fraction(index,parameters):
    count,_,_=validate(parameters)
    if int(index)!=index or index<0:raise ValueError('Invalid sequential particle index')
    if parameters.get('restart behavior (0 = bounce, 1 = loop )',False):return (int(index)%count)/(count-1)
    step=int(index)%(2*(count-1))
    return min(step,2*(count-1)-step)/(count-1)

def point(index,parameters,start,end):
    t=fraction(index,parameters)
    if len(start)!=3 or len(end)!=3 or not all(math.isfinite(float(v)) for v in (*start,*end)):raise ValueError('Invalid sequential path endpoints')
    return tuple(float(a)+(float(b)-float(a))*t for a,b in zip(start,end))
