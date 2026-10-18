"""Experimental delayed lifetime gate, not connected to production baking.

Only a single step enabling decay is modeled. Source operator activation at
engine ticks and its threshold semantics still require a native comparison.
Pure simulation-clock queries keep results independent of playback direction.
"""
import math
from particle_sim import simulation_at,continuous_births

def requires_extended_history(modules,requested):
    """A zero-time decay gate preserves the ordinary lifetime boundary."""
    return bool(requested and any(module['function']=='Lifespan Decay'
        and module['parameters'].get('operator enabled',True)
        and activation(module['parameters'])>0 for module in modules))

def activation(parameters):
    keys=('operator start fadein','operator end fadein','operator start fadeout',
          'operator end fadeout','operator fade oscillate')
    values=[float(parameters.get(key,0)) for key in keys]
    if not all(math.isfinite(value) and value>=0 for value in values):
        raise ValueError('Invalid delayed decay timing')
    start,end,out_start,out_end,oscillate=values
    if start!=end or out_start or out_end or oscillate:
        raise ValueError('Experimental decay requires one enabling step')
    return start

def living(births,segments,time,lifetimes,parameters):
    """Retain particles until both sampled lifetime and the enabling step pass.

    lifetimes maps birth indices to their original sampled lifetimes. Those
    lifetimes are never stretched for appearance or motion evaluation.
    """
    start=activation(parameters)
    continuous_births(segments,0)  # Validate the monotonic simulation clock.
    if not math.isfinite(time):raise ValueError('Invalid decay query time')
    clock=simulation_at(segments,time);result=[]
    for birth in births:
        life=float(lifetimes[birth.index])
        if not math.isfinite(life) or life<=0:
            raise ValueError('Particle lifetime must be finite and positive')
        death=max(birth.simulation_time+life,start)
        if birth.time<=time and clock<death-1e-10:
            result.append((birth,max(0.,clock-birth.simulation_time)))
    return result
