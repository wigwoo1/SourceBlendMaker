"""Installed SFM CPU trail corner layout (PET 0x10293e90).

The caller supplies sampled motion and length. This reproduces the observed
signed-width/camera-facing corners, not Source's simulation ticks.
SpriteCard's GPU spline path is outside this helper's scope.
"""
import math


def corners(center, tail_delta, width, eye, constrain=True):
    """Current +side, current -side, tail -side, tail +side; width is signed.

    Negative width exchanges sides without exchanging their texture corners.
    The constraint compares signed width with length, not abs(width).
    Omit invisible degenerate quads instead of inventing a side direction.
    """
    center=tuple(map(float,center));delta=tuple(map(float,tail_delta));eye=tuple(map(float,eye))
    width=float(width)
    if any(len(v)!=3 for v in (center,delta,eye)) or not all(math.isfinite(v) for v in (*center,*delta,*eye,width)):
        raise ValueError('Trail geometry requires finite xyz positions and width')
    length=math.hypot(*delta)
    if length<=1e-12 or width==0:return ()
    if constrain and width>length:width=length
    view=tuple(p-e for p,e in zip(center,eye))
    cross=(view[1]*delta[2]-view[2]*delta[1],view[2]*delta[0]-view[0]*delta[2],view[0]*delta[1]-view[1]*delta[0])
    norm=math.hypot(*cross)
    if norm<=1e-12:return ()
    side=tuple(v/norm*width*.5 for v in cross)
    tail=tuple(p+d for p,d in zip(center,delta))
    return (tuple(p+s for p,s in zip(center,side)),tuple(p-s for p,s in zip(center,side)),
            tuple(p-s for p,s in zip(tail,side)),tuple(p+s for p,s in zip(tail,side)))
