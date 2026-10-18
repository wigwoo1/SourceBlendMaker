"""Decoded Color Random tint blend with an explicitly supplied lighting query.

The installed scalar helper supplies five blend modes. Map queries, cache
ownership and engine scheduling are separate; normal conversion stays gated.
Source random streams and exact float32 rounding are not reproduced here.
"""
import math

def validate(parameters):
    settings(parameters)
    fraction=float(parameters.get('tint_perc',0))
    if not math.isfinite(fraction) or not 0<=fraction<=1:
        raise ValueError('Tint fraction must be finite and in 0-1')
    cp=parameters.get('tint control point',0)
    if isinstance(cp,bool) or not isinstance(cp,(int,float)) or not math.isfinite(cp) or int(cp)!=cp or not 0<=cp<64:
        raise ValueError('Invalid tint control point')
    threshold=float(parameters.get('tint update movement threshold',32.))
    if not math.isfinite(threshold) or threshold<0:
        raise ValueError('Invalid tint movement threshold')
    for key in ('color1','color2','tint clamp min','tint clamp max'):
        if key not in parameters:continue
        values=parameters[key][:3]
        if len(values)!=3 or any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=255 for v in values):
            raise ValueError('Invalid tint RGB bytes: '+key)
    low=parameters.get('tint clamp min',(0,0,0))[:3]
    high=parameters.get('tint clamp max',(255,255,255))[:3]
    if any(int(v)!=v for v in tuple(low)+tuple(high)) or any(a>b for a,b in zip(low,high)):
        raise ValueError('Invalid tint byte clamps')

def settings(parameters):
    mode=parameters.get('tint blend mode',0)
    if isinstance(mode,bool) or not isinstance(mode,(int,float)) or not math.isfinite(mode) or int(mode)!=mode or not 0<=mode<=4:
        raise ValueError('Unsupported tint blend mode')
    amplification=float(parameters.get('light amplification amount',1.))
    if not math.isfinite(amplification) or amplification<0:
        raise ValueError('Finite nonnegative tint amplification required')
    return int(mode),amplification

def blend(low,high,random_fraction,lighting,tint_fraction,mode):
    vectors=[tuple(float(x) for x in v) for v in (low,high,lighting)]
    if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError('Expected finite RGB vectors')
    low,high,lighting=vectors
    if any(not math.isfinite(v) or not 0<=v<=1 for v in (random_fraction,tint_fraction)):
        raise ValueError('Tint fractions must be finite and in 0-1')
    mode,_=settings({'tint blend mode':mode})
    base=tuple(a+(b-a)*random_fraction for a,b in zip(low,high))
    result=[]
    for color,light in zip(base,lighting):
        if mode==0:target=light
        elif mode==1:target=2*color*light if light<.5 else 1-2*(1-color)*(1-light)
        elif mode==2:target=min(color,light)
        elif mode==3:target=max(color,light)
        else:target=color*light
        result.append(min(1.,color+(target-color)*tint_fraction))
    return tuple(result)

def color(parameters,base,rng,query):
    """Query returns four cached lighting bytes; this function owns no cache."""
    validate(parameters)
    mode,amplification=settings(parameters)
    packed=tuple(query(parameters))
    if len(packed)!=4 or any(type(v) is not int or not 0<=v<=255 for v in packed):
        raise ValueError('Four cached lighting bytes required')
    low=tuple(parameters.get('tint clamp min',(0,0,0))[:3])
    high=tuple(parameters.get('tint clamp max',(255,255,255))[:3])
    if len(low)!=3 or len(high)!=3 or any(not isinstance(v,(int,float)) or not math.isfinite(v) or int(v)!=v or not 0<=v<=255 for v in low+high) or any(a>b for a,b in zip(low,high)):
        raise ValueError('Invalid tint byte clamps')
    import struct
    def f32(v):
        try:return struct.unpack('<f',struct.pack('<f',v))[0]
        except OverflowError:raise ValueError('Tint amplification overflows float32') from None
    lighting=tuple(f32(f32(max(a,min(b,v)))*f32(f32(amplification)/f32(255.))) for a,b,v in zip(low,high,packed))
    result=blend(tuple(float(v)/255. for v in parameters.get('color1',base)[:3]),
                 tuple(float(v)/255. for v in parameters.get('color2',base)[:3]),
                 rng.random(),lighting,float(parameters['tint_perc']),mode)
    from particle_sprite_state import linear_color
    return linear_color([v*255 for v in result])
