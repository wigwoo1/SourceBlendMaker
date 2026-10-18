"""Merge independent authored emitters on the shared simulation clock.

Source tick scheduling and random stream ordering remain approximate.
"""
import math,random
from particle_sim import Birth,continuous_births,emission_window,simulation_at
from particle_burst import validate_instantaneous_count

def validate(modules,allow_burst_scaling=False):
    for module in modules:
        p=module['parameters'];function=module['function']
        if function=='emit_continuously':
            # Installed continuous-emitter unpack table: omitted rate = 100.
            rate=float(p.get('emission_rate',100))
            if not math.isfinite(rate) or rate<0:raise ValueError('Emission rate must be finite and nonnegative')
        elif function=='emit noise':
            from particle_noise_emitter import validate as validate_noise
            validate_noise(p)
        elif function=='emit_instantaneously':
            if int(p.get('emission count scale control point',-1))>=0:
                if not allow_burst_scaling:raise ValueError('Control-point scaled bursts require animated CP binding')
                from particle_burst_scaling import settings as scaling_settings
                scaling_settings(p)
            if int(p.get('control point with snapshot data',-1))>=0:raise ValueError('Snapshot-scaled bursts are unsupported')
            if not math.isfinite(float(p.get('emission_start_time max',-1))):raise ValueError('Invalid burst start maximum')
        elif function=='emit to maintain count':
            from particle_maintain_count import target_count
            target_count(p)
            if len(modules)!=1:raise ValueError('Combined maintained and other emitters are unsupported')
            if int(p.get('maintain count scale control point',-1))>=0:raise ValueError('Maintained target control-point history is unsupported')
            start=float(p.get('emission start time',0))
            if not math.isfinite(start) or start<0:raise ValueError('Invalid maintain-count start time')
        else:raise ValueError('Unsupported emitter: '+function)
        if p.get('use parent particles for emission scaling',False) or float(p.get('scale emission to used control points',0))!=0:
            raise ValueError('Scaled particle emission is unsupported')
        from particle_emitter_fade import settings
        fades=settings(p)
        if function=='emit to maintain count' and any(fades):raise ValueError('Maintained emitter strength timing is unsupported')
        if function=='emit_instantaneously' and any(fades):raise ValueError('Burst emitter strength timing is unsupported')
        if function=='emit noise' and any(fades):raise ValueError('Noise emitter strength fades are unsupported')

def births(modules,segments,seed,frame_times=None,maximum_particles=1000,burst_scale_sample=None):
    validate(modules,allow_burst_scaling=burst_scale_sample is not None);merged=[]
    if any(m['function']=='emit to maintain count' for m in modules):
        raise ValueError('Maintained emission requires lifetime-aware scheduling')
    for emitter_index,module in enumerate(modules):
        p=module['parameters']
        if module['function']=='emit_continuously':
            duration=float(p.get('emission_duration',0))
            # Installed Source PCFs use -1 as the unbounded-emission sentinel.
            if duration==-1:duration=0.
            gated=emission_window(segments,float(p.get('emission_start_time',0)),duration)
            from particle_emitter_fade import continuous
            result=continuous(gated,float(p.get('emission_rate',100)),p)
        elif module['function']=='emit noise':
            from particle_noise_emitter import births as noise_births
            result=noise_births(p,segments)
        else:
            start=float(p.get('emission_start_time',0));result=[]
            if not math.isfinite(start) or start<0:raise ValueError('Invalid burst start')
            emitter_seed=seed if emitter_index==0 else str(seed)+':emitter:'+str(emitter_index)
            rng=random.Random(emitter_seed)
            count=int(p.get('num_to_emit',100));minimum=int(p.get('num_to_emit_minimum',-1))
            if minimum>=0:
                # Source normalizes reversed authored count bounds on unpack.
                if minimum>count:minimum,count=count,minimum
                if minimum<0:raise ValueError('Invalid burst particle count')
                count=rng.randint(minimum,count)
            start_maximum=float(p.get('emission_start_time max',-1))
            if start_maximum>0:
                # Preserve count-before-time draw ordering with our approximate RNG.
                start=start+(start_maximum-start)*rng.random()
            for segment in segments:
                if not segment.emitting or not segment.simulating:continue
                if simulation_at(segments,segment.end)<start:continue
                lo,hi=segment.start,segment.end
                if simulation_at(segments,lo)>=start:hi=lo
                else:
                    for _ in range(45):
                        mid=(lo+hi)*.5
                        if simulation_at(segments,mid)<start:lo=mid
                        else:hi=mid
                if int(p.get('emission count scale control point',-1))>=0:
                    from particle_burst_scaling import settings as scaling_settings,count as scaled_count
                    cp,field=scaling_settings(p)
                    # Initialize once at the first emitting crossing. Our
                    # continuous clock inverse approximates Source tick phase.
                    count=scaled_count(count,burst_scale_sample(cp,field,hi))
                maximum=int(p.get('maximum emission per frame',-1))
                if maximum < -1:raise ValueError('Invalid maximum emission per frame')
                if maximum==-1:
                    # Installed unpack normalizes the sentinel using definition capacity.
                    capacity=int(maximum_particles)
                    if capacity<=0:raise ValueError('Invalid maximum particle count')
                    maximum=min(capacity,5000)
                if maximum>=0 and count>maximum and frame_times is not None:
                    if maximum==0:raise ValueError('Positive burst with zero per-frame emission cap is unsupported')
                    if count<0 or count>1000000:raise ValueError('Invalid burst particle count')
                    ticks=[hi]+sorted({float(t) for t in frame_times if t>hi+1e-8})
                    for tick in ticks:
                        active=next((s for s in segments if s.start<=tick<s.end),None)
                        if active is None or not active.emitting or not active.simulating:continue
                        remaining=count-len(result)
                        result.extend(Birth(len(result)+i,tick,simulation_at(segments,tick)) for i in range(min(maximum,remaining)))
                        if len(result)==count:break
                else:
                    count=validate_instantaneous_count(count,maximum)
                    result=[Birth(i,hi,simulation_at(segments,hi)) for i in range(count)]
                break
        merged.extend((b.time,emitter_index,b.index,b.simulation_time) for b in result)
    merged.sort(key=lambda item:item[:3])
    return [Birth(i,time,clock) for i,(time,_,_,clock) in enumerate(merged)]
