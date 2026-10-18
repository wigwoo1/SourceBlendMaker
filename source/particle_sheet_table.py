"""Installed CSheet's 1024-entry interpolated UV table for dual SpriteCards.

Only the verified cycle-rate renderer path is enabled. Source visual parity
remains unverified. Raw sequence data comes from particle_sheet.
"""
import bisect
import math
import struct
from array import array
from collections import namedtuple

Sample=namedtuple('Sample','current following alternate_current alternate_following blend')
_FLOAT=struct.Struct('<f')


def f32(value):
    return _FLOAT.unpack(_FLOAT.pack(value))[0]


class Table:
    def __init__(self,entry):
        frames=entry['frames'];count=len(frames)
        if not 1<=count<=1024:
            raise ValueError('Sheet table requires 1..1024 frames')
        declared=float(entry['duration'])
        if not math.isfinite(declared) or not 1<=math.trunc(declared)<2**31:
            raise ValueError('Sheet table requires a positive declared integer-duration denominator')
        inverse=f32(1./f32(math.trunc(declared)))
        current=[];alternate=[];keys=[];elapsed=0.
        for frame in frames:
            duration=float(frame['duration']);coords=frame['coordinates']
            if not math.isfinite(duration) or duration<=0:
                raise ValueError('Zero/negative sheet frame durations need separate boundary verification')
            if len(coords) not in (1,4) or any(len(rect)!=4 or not all(math.isfinite(float(v)) for v in rect) for rect in coords):
                raise ValueError('Invalid sheet coordinate sets')
            current.append(tuple(f32(v) for v in coords[0]))
            alternate.append(tuple(f32(v) for v in coords[1 if len(coords)==4 else 0]))
            keys.append(f32(f32(inverse*elapsed)*1024.))
            elapsed=f32(elapsed+f32(duration))
        if not math.isfinite(elapsed) or any(b<=a for a,b in zip(keys,keys[1:])):
            raise ValueError('Sheet table has non-increasing normalized frame times')
        self.keys=tuple(keys);self.frame_count=count;self.duration=elapsed
        self.clamp=bool(entry['clamp']);self.data=array('f')
        for index in range(1 if count==1 else 1024):
            upper=bisect.bisect_left(keys,float(index))
            if upper==0:
                if self.clamp:lower=upper=0;blend=1.
                else:
                    lower=count-1
                    gap=f32(1024.-keys[-1]);denominator=f32(gap+keys[0])
                    if denominator==0:raise ValueError('Degenerate sheet wrap interval')
                    blend=f32(f32(float(index)+gap)/denominator)
            elif upper==count:
                if self.clamp:lower=upper=count-1;blend=1.
                else:
                    lower=count-1;upper=0
                    denominator=f32(f32(1024.-keys[-1])+keys[0])
                    if denominator==0:raise ValueError('Degenerate sheet wrap interval')
                    blend=f32(f32(float(index)-keys[-1])/denominator)
            else:
                lower=upper-1
                blend=f32(f32(float(index)-keys[lower])/f32(keys[upper]-keys[lower]))
            self.data.extend((*current[lower],*current[upper],*alternate[lower],*alternate[upper],blend))

    def at(self,index):
        if isinstance(index,bool) or not isinstance(index,int):
            raise ValueError('Sheet sample index must be an integer')
        if self.frame_count==1:index=0
        elif self.clamp:index=min(index&0xffffffff,1023)
        else:index&=1023
        start=index*17;values=self.data[start:start+17]
        return Sample(tuple(values[:4]),tuple(values[4:8]),tuple(values[8:12]),tuple(values[12:16]),values[16])

    def sample(self,age,rate):
        """Rate is cycles/second after the renderer's timing conversion."""
        age,rate=float(age),float(rate)
        if not all(math.isfinite(v) for v in (age,rate)):
            raise ValueError('Sheet time and rate must be finite')
        # PET stores bound_rate=float32(rate*1024), then its x87 helper
        # multiplies float32 age and bound_rate before truncation to int64.
        value=f32(age)*f32(f32(rate)*1024.)
        if not -(2**63)<=value<2**63:
            raise ValueError('Sheet sample clock exceeds the verified integer range')
        return self.at(math.trunc(value)&0xffffffff)
