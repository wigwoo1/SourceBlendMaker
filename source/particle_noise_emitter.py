"""Installed noise rate math with approximate offline 120 Hz scheduling.

The rate formula and count floor follow static installed PET instructions;
tick phase, engine random streams and control-point-scaled rates are unverified.
"""
import math,json
from pathlib import Path
from particle_noise import noise,f32
from particle_sim import Birth,continuous_births,emission_window,simulation_at

_tables=None
def tables():
    global _tables
    if _tables is None:
        data=json.loads(Path(__file__).with_name('particle_noise_tables.json').read_text())
        _tables=[t['values'] for t in data['tables']]
        if len(_tables)!=4 or any(len(t)!=256 for t in _tables):
            raise ValueError('Invalid noise lookup tables')
    return _tables

def validate(parameters):
    rate(parameters,0,tables())
    start=float(parameters.get('emission_start_time',0))
    duration=float(parameters.get('emission_duration',0))
    if not all(math.isfinite(v) and v>=0 for v in (start,duration)):
        raise ValueError('Invalid noise emission window')

def rate(parameters,clock,tables):
    if float(parameters.get('world time noise coordinate scale',0))!=0:
        raise ValueError('World-time random noise coordinates are not implemented')
    if float(parameters.get('scale emission to used control points',0))!=0:
        raise ValueError('Control-point emission scaling is not implemented')
    low=float(parameters.get('emission minimum',0))
    high=float(parameters.get('emission maximum',100))
    scale=float(parameters.get('time noise coordinate scale',.1))
    offset=float(parameters.get('time coordinate offset',0))
    if not all(math.isfinite(v) for v in (low,high,scale,offset,clock)) or min(low,high)<0:
        raise ValueError('Invalid noise emitter parameters')
    coordinate=f32(f32(f32(clock)+f32(offset))*f32(scale))
    value=noise((coordinate,)*3,tables)
    absolute=bool(parameters.get('absolute value',False))
    if absolute:value=abs(value)
    if parameters.get('invert absolute value',False):value=f32(1-value)
    span=f32(f32(high)-f32(low));factor=1. if absolute else .5
    slope=f32(span*factor)
    base=f32(f32((1-factor)*span)+f32(low))
    return max(0.,f32(f32(slope*value)+base))

def births(parameters,segments,noise_tables=None,tick_rate=120.,max_particles=1000000,rate_function=None):
    continuous_births(segments,0)  # Validate the shared simulation clock.
    if not math.isfinite(tick_rate) or tick_rate<=0:raise ValueError('Invalid simulation tick rate')
    gated=emission_window(segments,float(parameters.get('emission_start_time',0)),float(parameters.get('emission_duration',0)))
    noise_tables=noise_tables or tables()
    result=[];total=0.;emitted=0;steps=0;sample=rate_function or (lambda clock:rate(parameters,clock,noise_tables))
    for segment in gated:
        if not segment.simulating or not segment.emitting:continue
        time=segment.start
        while time<segment.end-1e-12:
            steps+=1
            if steps>1000000:raise ValueError('Noise simulation exceeds step limit')
            end=min(segment.end,time+1/tick_rate)
            before=simulation_at(segments,time);after=simulation_at(segments,end)
            r=float(sample(after))
            if not math.isfinite(r) or r<0:raise ValueError('Invalid sampled emission rate')
            total+=f32(f32(after-before)*f32(r))
            count=math.floor(total)-emitted;emitted+=count
            if len(result)+count>max_particles:raise ValueError('Particle count exceeds prototype limit')
            # Installed emitter spreads this tick's births uniformly through
            # its active time interval, including the endpoint.
            for i in range(count):
                born=time+(end-time)*(i+1)/count
                result.append(Birth(len(result),born,simulation_at(segments,born)))
            time=end
    return result
