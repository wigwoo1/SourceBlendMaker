"""Approximate ordered opacity history with birth-based fade writes.

Engine tick phase and exact interaction between Source alpha operators remain
unverified. Random oscillator parameters must already be sampled at birth.
"""
import math

def alpha(definition,state,age,lifetime,fade_durations=None,step=1/120):
    from particle_bake import appearance
    from particle_scalar_remap import remap
    from particle_scalar_oscillation import increment,f32,settings
    if not all(math.isfinite(v) for v in (age,lifetime,step)) or age<0 or lifetime<=0 or step<=0:raise ValueError('Invalid alpha history interval')
    ticks=math.floor(age/step)
    if ticks>1000000:raise ValueError('Alpha history exceeds simulation limit')
    times=[i*step for i in range(ticks+1)]
    if times[-1]<age:times.append(age)
    oscillators={index:settings(state.get('scalar_oscillations',{}).get(index,m['parameters'])) for index,m in enumerate(definition['modules']['operators']) if m['function']=='Oscillate Scalar' and m['parameters'].get('operator enabled',True) and m['parameters'].get('oscillation field',7)==7}
    initial=float(state['alpha']);current=initial;previous=0.
    for time in times:
        enabled_index=-1
        for index,module in enumerate(definition['modules']['operators']):
            p=module['parameters'];name=module['function']
            if not p.get('operator enabled',True):continue
            enabled_index+=1
            if name=='Oscillate Scalar' and p.get('oscillation field',7)==7:
                sampled=oscillators[index]
                current=f32(current+increment(sampled,time,lifetime,time-previous))
                current=min(1.,max(0.,current))
            elif name=='Remap Scalar' and p['output field']==7:
                value={1:lifetime,7:current,8:state['creation_simulation_time']}[p['input field']]
                current=remap(p,value,current)
            elif name in ('Alpha Fade In Simple','Alpha Fade Out Simple'):
                from particle_bake import simple_fade_value
                current=simple_fade_value(name,p,time/lifetime,current,initial)
            elif name in ('Alpha Fade and Decay','Alpha Fade In Random','Alpha Fade Out Random'):
                single={**definition,'modules':{**definition['modules'],'operators':[module]}}
                durations={0:fade_durations[enabled_index]} if fade_durations and enabled_index in fade_durations else None
                if name=='Alpha Fade and Decay':
                    from particle_scalar_remap import ordered_alpha
                    current=ordered_alpha(single,{'alpha':initial},time,lifetime)
                else:current=initial*appearance(single,time,lifetime,1.,durations)[1]
            elif name=='Oscillate Scalar Simple' and int(p.get('oscillation field',7))==7:
                from particle_oscillation import delta
                current=min(1.,max(0.,current+delta(p,time)-delta(p,previous)))
        previous=time
    if not math.isfinite(current):raise ValueError('Invalid resulting particle alpha')
    return min(1.,max(0.,current))
