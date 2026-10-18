"""Deterministic continuous-emission clock for offline particle baking.

This implements a mathematical emission approximation, not Source's tick/RNG
implementation. Segments must split at every flag or speed-interpolation change.
"""
import math
from bisect import bisect_left
from dataclasses import dataclass

@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    emitting: bool=True
    simulating: bool=True
    speed_start: float=1.0
    speed_end: float=1.0

@dataclass(frozen=True)
class Birth:
    index: int
    time: float
    simulation_time: float

def shot_segments(shot,system,start,end):
    """Split at the actual global times of all particle control keys."""
    points={float(start),float(end)}
    for attribute in ('emitting','simulating','simulationTimeScale'):
        curve=shot.curves.get((str(system.id),attribute,0))
        if curve:
            for times,_ in curve.layers:
                for time in times:
                    global_time=curve.clock.global_time(time)
                    if start<global_time<end:points.add(global_time)
    result=[];points=sorted(points)
    for a,b in zip(points,points[1:]):
        middle=(a+b)*.5
        result.append(Segment(a,b,bool(shot.value(system,'emitting',middle,True)),
                              bool(shot.value(system,'simulating',middle,True)),
                              float(shot.value(system,'simulationTimeScale',a,1.)),
                              float(shot.value(system,'simulationTimeScale',math.nextafter(b,a),1.))))
    return result

def continuous_births(segments,rate,max_particles=1000000):
    """Carry fractional emission across gates; freeze the clock while paused.

    Births occur at each accumulated 1/rate simulation second. Linear speed
    ramps are integrated and inverted analytically, so output is independent
    of frame subdivision. Negative speed is unsupported rather than reversed.
    """
    if not math.isfinite(rate) or rate<0:raise ValueError('Emission rate must be finite and nonnegative')
    simulation=0.;phase=0.;births=[];previous=None
    for segment in segments:
        a,b=segment.start,segment.end;u,v=segment.speed_start,segment.speed_end
        if not all(math.isfinite(x) for x in (a,b,u,v)) or b<a or min(u,v)<0:
            raise ValueError('Invalid particle clock segment')
        if previous is not None and abs(a-previous)>1e-8:raise ValueError('Particle clock segments must be contiguous')
        previous=b
        duration=b-a
        if not segment.simulating or not duration:continue
        elapsed=duration*(u+v)*.5
        if segment.emitting and rate and elapsed:
            amount=elapsed*rate
            count=math.floor(phase+amount+1e-10)
            if len(births)+count>max_particles:raise ValueError('Particle bake exceeds configured particle limit')
            slope=(v-u)/duration
            for i in range(count):
                delta=(i+1-phase)/rate
                if abs(slope)<1e-12:offset=delta/u
                else:
                    # Stable quadratic root; avoids subtracting similar values.
                    offset=2*delta/(u+math.sqrt(max(0,u*u+2*slope*delta)))
                births.append(Birth(len(births),a+min(duration,max(0,offset)),simulation+delta))
            phase=phase+amount-count
        simulation+=elapsed
    return births

def emission_window(segments,start=0.,duration=0.):
    """Gate emission in simulation time while leaving the simulation clock intact."""
    if not all(math.isfinite(v) and v>=0 for v in (start,duration)):raise ValueError(f'Invalid emission time window: start={start!r}, duration={duration!r}; negative duration sentinel behavior is not verified')
    stop=start+duration if duration else math.inf
    result=[]
    for segment in segments:
        points={segment.start,segment.end}
        if segment.simulating:
            for threshold in (start,stop):
                if simulation_at(segments,segment.start)<threshold<simulation_at(segments,segment.end):
                    a,b=segment.start,segment.end
                    for _ in range(50):
                        middle=(a+b)*.5
                        if simulation_at(segments,middle)<threshold:a=middle
                        else:b=middle
                    points.add((a+b)*.5)
        points=sorted(points)
        length=segment.end-segment.start
        for a,b in zip(points,points[1:]):
            clock=simulation_at(segments,(a+b)*.5)
            def speed(time):return segment.speed_start+(segment.speed_end-segment.speed_start)*(time-segment.start)/length if length else segment.speed_start
            result.append(Segment(a,b,segment.emitting and start<=clock<stop,segment.simulating,speed(a),speed(b)))
    return result

def simulation_at(segments,time):
    result=0.
    for segment in segments:
        if time<=segment.start:break
        if segment.simulating and segment.end>segment.start:
            dt=min(time,segment.end)-segment.start
            slope=(segment.speed_end-segment.speed_start)/(segment.end-segment.start)
            result+=segment.speed_start*dt+slope*dt*dt*.5
        if time<=segment.end:break
    return result

def simulation_clock_samples(segments,times):
    """Precompute clock values once for frame/event scheduling."""
    values=list(times)
    return [simulation_at(segments,time) for time in values]

def delayed_segments(segments,delay):
    """Start a child clock at its inherited delay in the parent simulation clock."""
    gated=emission_window(segments,delay)
    return [Segment(s.start,s.end,s.emitting,s.simulating and simulation_at(segments,(s.start+s.end)*.5)>=delay,
                    s.speed_start,s.speed_end) for s in gated]

def living(births,segments,time,lifetime):
    if lifetime<=0 or not math.isfinite(lifetime):raise ValueError('Particle lifetime must be finite and positive')
    clock=simulation_at(segments,time)
    return [(birth,max(0.,clock-birth.simulation_time)) for birth in births
            if birth.time<=time and clock-birth.simulation_time<lifetime-1e-10]

def active_frame_samples(births,segments,frames,seconds,lifetimes):
    """Yield only requested frames containing live births, without rescanning all births.

    ``lifetimes`` maps accepted birth indices to their initialized lifetimes.
    The simulation clock is monotonic because negative simulation speeds are
    rejected by ``shot_segments``/the emitter planner, so birth/death events
    can be scheduled once and maintained with a small active set. This keeps
    the sampled age identical to :func:`living`, including pauses and speed
    ramps, while avoiding an O(frames * births) scan over dead/future births.
    """
    if len(frames)!=len(seconds):raise ValueError('Particle frames and times must have equal lengths')
    if not frames:return
    clocks=simulation_clock_samples(segments,seconds)
    starts={};ends={}
    for birth in births:
        lifetime=lifetimes.get(birth.index)
        if lifetime is None or lifetime<=0 or not math.isfinite(lifetime):continue
        first=bisect_left(seconds,birth.time)
        if first>=len(seconds):continue
        # living() requires age < lifetime - epsilon.
        last=bisect_left(clocks,birth.simulation_time+lifetime-1e-10)
        last=min(last,len(seconds))
        if last<=first:continue
        starts.setdefault(first,[]).append(birth)
        ends.setdefault(last,[]).append(birth.index)
    active={}
    for sample_index,(frame,time,clock) in enumerate(zip(frames,seconds,clocks)):
        for index in ends.get(sample_index,()):active.pop(index,None)
        for birth in starts.get(sample_index,()):active[birth.index]=birth
        if active:
            alive=[(birth,max(0.,clock-birth.simulation_time)) for birth in active.values()]
            yield sample_index,frame,time,alive
