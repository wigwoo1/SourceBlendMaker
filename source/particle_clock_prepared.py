"""Prepared inverse preserving the reference's tolerance branches."""
import math,bisect
from particle_sim import continuous_births,simulation_at

class PreparedInverse:
    def __init__(self,segments):
        continuous_births(segments,0)
        if not segments:raise ValueError('Empty particle clock')
        self.segments=tuple(segments);self.total=simulation_at(segments,segments[-1].end)
        self.starts=[];self.ends=[];self.rows=[];accumulated=0.
        for segment in segments:
            duration=segment.end-segment.start
            elapsed=duration*(segment.speed_start+segment.speed_end)*.5 if segment.simulating else 0.
            self.starts.append(accumulated);self.ends.append(accumulated+elapsed)
            self.rows.append((segment,duration,elapsed,accumulated));accumulated+=elapsed

    def query(self,clock,side='right',minimum_time=None):
        segments=self.segments
        if not math.isfinite(clock) or clock<0 or side not in ('left','right'):
            raise ValueError('Invalid clock inverse query')
        if clock>self.total+1e-10:raise ValueError('Clock query exceeds history')
        if minimum_time is not None and (not math.isfinite(minimum_time) or not segments[0].start<=minimum_time<=segments[-1].end):
            raise ValueError('Invalid minimum history time')
        candidates=[]
        first=bisect.bisect_left(self.ends,clock-1e-10)
        last=bisect.bisect_right(self.starts,clock+1e-10)
        for segment,duration,elapsed,accumulated in self.rows[first:last]:
            if elapsed<=0:
                if abs(clock-accumulated)<=1e-10:candidates.extend((segment.start,segment.end))
            elif accumulated-1e-10<=clock<=accumulated+elapsed+1e-10:
                delta=min(elapsed,max(0.,clock-accumulated))
                slope=(segment.speed_end-segment.speed_start)/duration
                if abs(slope)<1e-12:offset=delta/segment.speed_start
                elif delta==0:offset=0.
                else:offset=2*delta/(segment.speed_start+math.sqrt(max(0.,segment.speed_start**2+2*slope*delta)))
                candidates.append(segment.start+min(duration,max(0.,offset)))
        if minimum_time is not None:
            if abs(simulation_at(segments,minimum_time)-clock)<=1e-10:candidates.append(minimum_time)
            candidates=[value for value in candidates if value>=minimum_time-1e-10]
        if not candidates:raise ValueError('No history time matches clock')
        return min(candidates) if side=='left' else max(candidates)
