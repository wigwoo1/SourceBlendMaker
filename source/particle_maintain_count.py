"""Maintain-count emission batch arithmetic from installed Source static code.

The caller must supply the live count, resolved target, capacity and clock.
This does not yet resolve control-point targets or simulate particle deaths.
"""
import math

def target_count(parameters,control_point_value=None):
    """Resolve a fixed target or a caller-sampled control-point vector target.

    Snapshot particle counts require snapshot data and are not supported here.
    """
    if int(parameters.get('control point with snapshot data',-1))>=0:
        raise ValueError('Maintain-count snapshot targets are unsupported')
    count=parameters.get('count to maintain',100)
    if isinstance(count,bool) or not isinstance(count,int) or count<0:
        raise ValueError('Invalid maintain-count target')
    point=int(parameters.get('maintain count scale control point',-1))
    field=min(2,max(0,int(parameters.get('maintain count scale control point field',0))))
    if point>=0:
        if control_point_value is None or len(control_point_value)!=3:
            raise ValueError('Maintain-count target requires a sampled control point')
        value=float(control_point_value[field])
        if not math.isfinite(value):raise ValueError('Invalid maintain-count control-point value')
        count=max(0,int(count*value))
    return count

def batch_times(live_count,target_count,capacity,previous_time,current_time,start_time):
    """Return the missing particles' creation times within this simulation tick."""
    counts=(live_count,target_count,capacity)
    if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in counts):
        raise ValueError('Particle counts must be nonnegative integers')
    previous_time,current_time,start_time=map(float,(previous_time,current_time,start_time))
    if not all(math.isfinite(v) for v in (previous_time,current_time,start_time)) or current_time<previous_time:
        raise ValueError('Invalid maintain-count simulation interval')
    if current_time<start_time:return []
    count=max(0,min(capacity-live_count,target_count-live_count))
    if not count:return []
    beginning=max(previous_time,start_time)
    increment=(current_time-beginning)/count
    return [min(current_time,beginning+index*increment) for index in range(count)]

def schedule(segments,parameters,capacity,lifetime_at_birth,step=1/120,max_births=1000000):
    """Approximate fixed-clock replacement history for a fixed target.

    Expired particles are removed before each refill. Source death/emit ordering
    and tick phase remain unverified. Control-point and snapshot targets require
    a history-aware caller and are rejected by this scheduler.
    """
    from particle_sim import simulation_at,continuous_births,Birth
    from particle_clock_inverse import real_time
    continuous_births(segments,0)  # Validate clock segments, including pauses.
    if not math.isfinite(step) or step<=0:raise ValueError('Invalid maintain-count tick interval')
    if int(parameters.get('maintain count scale control point',-1))>=0:
        raise ValueError('Maintain-count scheduler requires a fixed target')
    target=target_count(parameters)
    start=float(parameters.get('emission start time',0))
    if not math.isfinite(start) or start<0:raise ValueError('Invalid maintain-count start time')
    if not segments:return []
    if isinstance(capacity,bool) or not isinstance(capacity,int) or capacity<0:
        raise ValueError('Invalid maintain-count capacity')
    births=[];live=[]
    total=simulation_at(segments,segments[-1].end)
    if total/step>1000000:raise ValueError('Maintain-count scheduler exceeds tick limit')
    previous=0.
    for tick in range(math.ceil(total/step)+1):
        clock=min(total,tick*step)
        time=real_time(segments,clock,side='right')
        segment=next((s for s in segments if s.start<=time<s.end),segments[-1])
        live=[entry for entry in live if clock-entry[0].simulation_time<entry[1]]
        if segment.emitting and segment.simulating:
            times=batch_times(len(live),target,capacity,previous,clock,start)
            if len(births)+len(times)>max_births:raise ValueError('Maintain-count scheduler exceeds birth limit')
            for born in times:
                birth=Birth(len(births),real_time(segments,born,side='right'),born)
                life=float(lifetime_at_birth(birth))
                if not math.isfinite(life) or life<=0:raise ValueError('Invalid maintained particle lifetime')
                births.append(birth);live.append((birth,life))
        previous=clock
    return births
