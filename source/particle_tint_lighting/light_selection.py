"""Experimental ordered slot reduction, after external PVS/eligibility filtering.

Models 0x10197490..0x101975ab and its minimum helper only. Does not sample
lighting or decide eligibility. Overflow returns contributions for cube folding.
"""
import math
from particle_tint_lighting.point_light import f32

def select(candidates, capacity):
    return select_stream(((identifier,score,True) for identifier,score in candidates),capacity)


def select_stream(candidates, capacity):
    """Keep immediate low-priority folding interleaved with slot displacement."""
    if type(capacity) is not int or not 0 <= capacity <= 4:
        raise ValueError('Runtime cache supports zero to four slots')
    slots=[]; folded=[]
    for identifier,score,selectable in candidates:
        if not math.isfinite(score) or score<0:
            raise ValueError('Finite nonnegative score required')
        candidate=(identifier,f32(score))
        if type(selectable) is not bool:raise ValueError('Explicit selectable flag required')
        if not selectable:
            folded.append(candidate);continue
        if len(slots)<capacity:
            slots.append(candidate)
            continue
        threshold=f32(100000.); index=None
        for i,(_,stored) in enumerate(slots):
            if stored < threshold:
                threshold=stored; index=i
        if index is None:
            folded.append(candidate)
        else:
            folded.append(slots[index]); slots[index]=candidate
    return {'selected':slots,'folded':folded}
