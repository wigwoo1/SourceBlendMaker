"""Parent initializer position arithmetic, awaiting collection integration.

Inputs are Source-unit current/previous buffers, not render mesh positions.
The caller owns live-parent ordering, death handling, RNG and selection state.
Evidence: installed pet.dll scalar initializer 0x10230ac0..0x10231118.
"""
import math
from particle_scalar_oscillation import f32


def selection(count, cursor, increment=1., random_value=None):
    """Select a parent-buffer index and return the next initializer cursor.

    random_value is a supplied Source-style [0,1) draw. This helper does not
    reproduce the engine random stream. A fractional increment selects a
    continuous index; an integer increment selects a discrete random parent.
    Sequential overflow resets to zero, discarding the excess.
    """
    if not isinstance(count,int) or isinstance(count,bool) or count<=0:
        raise ValueError('An active nonempty parent buffer is required')
    if not all(math.isfinite(float(v)) for v in (cursor,increment)):
        raise ValueError('Finite parent selection state required')
    cursor,increment=f32(cursor),f32(increment)
    if cursor<0 or increment<0:
        raise ValueError('Negative parent selection state remains unsupported')
    fractional=increment!=math.floor(increment)
    if random_value is not None:
        if not math.isfinite(float(random_value)) or not 0<=random_value<1:
            raise ValueError('Parent random draw must be in [0,1)')
        draw=f32(random_value)
        if draw>=1:raise ValueError('Float32 parent random draw must remain below one')
        index=f32(draw*f32(count-1 if fractional else count))
        if not fractional:index=f32(math.trunc(index))
    else:
        index=0. if cursor>count-1 else cursor
    return index,f32(index+increment)


def birth_fraction(creation_time, current_time, timestep):
    """Source's float32 creation fraction, including a rounded-away tick.

    When current-minus-step equals current at float32 precision, Source uses
    a step at the current time rather than dividing by the supplied timestep.
    """
    if not all(math.isfinite(float(v)) for v in (creation_time,current_time,timestep)) or timestep<0:
        raise ValueError('Finite creation time and nonnegative timestep required')
    creation,current,step=map(f32,(creation_time,current_time,timestep))
    previous=f32(current-step)
    if previous==current:return float(creation>=current)
    return f32(min(1.,max(0.,f32(f32(creation-previous)/f32(current-previous)))))


def buffer_position(current, previous, index, fraction, inherited_scale=0):
    """Sample matching ordered parent buffers, spatially then temporally.

    Fractional indices blend floor/ceil parent entries in both buffers before
    birth-time interpolation. The caller must supply the actual simulation
    buffers with matching particle identity/order, including any killed-parent
    dispatch view. Empty buffers are not replaced with fabricated positions.
    """
    if not current or len(current)!=len(previous):
        raise ValueError('Matching nonempty parent buffers required')
    if not math.isfinite(float(index)) or not 0<=index<=len(current)-1:
        raise ValueError('Parent index outside active buffer')
    index=f32(index)
    lo=math.floor(index);hi=min(math.ceil(index),len(current)-1)
    weight=f32(index-f32(lo))
    def blend(buffer):
        a,b=buffer[lo],buffer[hi]
        if len(a)!=3 or len(b)!=3 or not all(math.isfinite(float(v)) for v in (*a,*b)):
            raise ValueError('Finite three-component parent buffers required')
        return tuple(f32(f32(x)+f32(f32(f32(y)-f32(x))*weight)) for x,y in zip(a,b))
    return position(blend(current),blend(previous),fraction,inherited_scale)


def position(current, previous, fraction, inherited_scale=0):
    """Return child current/previous at a clamped birth fraction of a tick.

    Inherited displacement is measured from the selected parent's previous
    position to the interpolated birth position, rather than the full tick.
    """
    if len(current)!=3 or len(previous)!=3:
        raise ValueError('Parent positions require three components')
    values=[*current,*previous,fraction,inherited_scale]
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('Finite parent position inputs required')
    t=f32(min(1.,max(0.,float(fraction))))
    scale=f32(inherited_scale)
    out=[];old=[]
    for c,p in zip(current,previous):
        c,p=f32(c),f32(p)
        x=f32(p+f32(f32(c-p)*t))
        out.append(x)
        old.append(f32(x+f32(f32(p-x)*scale)))
    return tuple(out),tuple(old)
