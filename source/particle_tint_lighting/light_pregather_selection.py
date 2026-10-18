"""Experimental first cache-gather slot selection, 0x101967c0..0x10196814.

Inputs must already pass baked/PVS/bounds/attenuation checks. Unlike the later
point query's fixed 100000 threshold, this pass supplies the incoming score to
the minimum-slot helper. Fold event values are ranks, not color contributions.
"""
import math
from particle_tint_lighting.point_light import f32

def select_stream(candidates,capacity):
    if type(capacity) is not int or not 0<=capacity<=4:
        raise ValueError('Explicit zero-to-four cache light capacity required')
    slots=[];folded=[];events=[];seen=set()
    for identifier,score,selectable in candidates:
        if identifier in seen:raise ValueError('Duplicate candidate ID')
        seen.add(identifier)
        if not math.isfinite(score) or score<0 or type(selectable) is not bool:
            raise ValueError('Finite nonnegative score and explicit selection flag required')
        score=f32(score)
        if not math.isfinite(score):raise ValueError('Rank outside float32 range')
        candidate=(identifier,score)
        if not selectable:
            folded.append(candidate);events.append(dict(kind='incoming',candidate=candidate));continue
        if len(slots)<capacity:
            slots.append(candidate);continue
        minimum=score;index=None
        for i,(_,stored) in enumerate(slots):
            if stored<minimum:minimum=stored;index=i
        if index is None:
            folded.append(candidate);events.append(dict(kind='incoming',candidate=candidate))
        else:
            folded.append(slots[index]);events.append(dict(kind='displaced',candidate=slots[index]))
            slots[index]=candidate
    return dict(selected=slots,folded=folded,fold_events=events,full_gather_implemented=False)
