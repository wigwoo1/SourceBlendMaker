"""World-axis twist force arithmetic from installed force 0x101fb170.

Development helper; not yet routed by the baker. SSE reciprocal-square-root
rounding is replaced by Python arithmetic. Local-axis conversion is pending.
"""
import math

def vector(value):
    if len(value)!=3:raise ValueError('Expected twist vector with three components')
    result=tuple(map(float,value))
    if not all(math.isfinite(v) for v in result):raise ValueError('Nonfinite twist vector')
    return result

def settings(parameters):
    if parameters.get('object local space axis 0/1',False):
        raise ValueError('Local twist axis transformation is unverified')
    from particle_epitrochoid import validate as validate_shared
    validate_shared({k:v for k,v in parameters.items() if k.startswith('operator ')})
    cp=float(parameters.get('control point',0));amount=float(parameters.get('amount of force',0))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<64 or not math.isfinite(amount):
        raise ValueError('Invalid twist control point/amount')
    axis=vector(parameters.get('twist axis',(0,0,1)))
    length=math.sqrt(sum(v*v for v in axis))
    if length==0:raise ValueError('Zero twist axis')
    return {'control_point':int(cp),'amount':amount,'axis':tuple(v/length for v in axis)}

def acceleration(config,position,origin):
    delta=tuple(a-b for a,b in zip(vector(position),vector(origin)))
    squared=sum(v*v for v in delta)
    if squared<=2**-23:return (0.,0.,0.)
    radial=tuple(v/math.sqrt(squared) for v in delta);axis=config['axis']
    dot=sum(a*b for a,b in zip(radial,axis))
    # Preserve the installed subtract sequence: radial - radial * dot.
    # This is not the conventional projection radial - axis * dot.
    reduced=tuple(v*(1-dot) for v in radial)
    reduced_squared=sum(v*v for v in reduced)
    if reduced_squared<=2**-23:return (0.,0.,0.)
    x,y,z=(v/math.sqrt(reduced_squared) for v in reduced);a,b,c=axis
    return tuple(config['amount']*v for v in (y*c-z*b,z*a-x*c,x*b-y*a))
