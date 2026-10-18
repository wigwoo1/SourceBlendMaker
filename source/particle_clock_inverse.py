"""Inverse of the converter's mathematical clock, not verified Source timing.

Paused clocks are ambiguous: callers must select the beginning or end of a
plateau explicitly. Birth history can constrain queries to a minimum real time.
"""
import math
from particle_sim import continuous_births,simulation_at

def real_time(segments,clock,side='right',minimum_time=None):
    continuous_births(segments,0)
    if not segments or not math.isfinite(clock) or clock<0 or side not in ('left','right'):
        raise ValueError('Invalid clock inverse query')
    total=simulation_at(segments,segments[-1].end)
    if clock>total+1e-10:raise ValueError('Clock query exceeds history')
    if minimum_time is not None and (not math.isfinite(minimum_time) or not segments[0].start<=minimum_time<=segments[-1].end):
        raise ValueError('Invalid minimum history time')
    candidates=[]
    accumulated=0.
    for segment in segments:
        duration=segment.end-segment.start
        elapsed=duration*(segment.speed_start+segment.speed_end)*.5 if segment.simulating else 0.
        if elapsed<=0:
            if abs(clock-accumulated)<=1e-10:candidates.extend((segment.start,segment.end))
        elif accumulated-1e-10<=clock<=accumulated+elapsed+1e-10:
            delta=min(elapsed,max(0.,clock-accumulated))
            slope=(segment.speed_end-segment.speed_start)/duration
            if abs(slope)<1e-12:offset=delta/segment.speed_start
            elif delta==0:offset=0.
            else:offset=2*delta/(segment.speed_start+math.sqrt(max(0.,segment.speed_start**2+2*slope*delta)))
            candidates.append(segment.start+min(duration,max(0.,offset)))
        accumulated+=elapsed
    if minimum_time is not None:
        if abs(simulation_at(segments,minimum_time)-clock)<=1e-10:candidates.append(minimum_time)
        candidates=[value for value in candidates if value>=minimum_time-1e-10]
    if not candidates:raise ValueError(f'No history time matches clock {clock!r} after minimum time {minimum_time!r}')
    return min(candidates) if side=='left' else max(candidates)
