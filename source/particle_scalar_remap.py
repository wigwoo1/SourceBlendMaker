"""Scalar remap math decoded from installed PET routine 0x10272c20.

Integration and Source simulation parity remain unverified.
"""
import math

def remap(parameters,input_value,current_value,strength=1.):
    values=[float(parameters.get(key,default)) for key,default in
            (('input minimum',0),('input maximum',1),('output minimum',0),('output maximum',1))]
    value,current,strength=map(float,(input_value,current_value,strength))
    if not all(math.isfinite(v) for v in values+[value,current,strength]):
        raise ValueError('Invalid scalar remap values')
    low,high,start,end=values
    output=float(parameters.get('output field',3))
    if not math.isfinite(output) or output!=int(output) or not 0<=output<32:
        raise ValueError('Invalid scalar remap output field')
    if int(output) in (7,16):
        start=min(1.,max(0.,start));end=min(1.,max(0.,end))
    amount=float(value>=high) if low==high else min(1.,max(0.,(value-low)/(high-low)))
    target=start+(end-start)*amount
    return current+(target-current)*strength

def ordered_alpha(definition,state,age,lifetime,fade_durations=None):
    """Evaluate supported alpha operations in authored order, including overwrite.

    Only creation time, lifetime and current alpha remap inputs are handled.
    Production planning must reject other fields and nonconstant strength.
    """
    from particle_bake import appearance,enabled
    from particle_sprite_state import fraction
    alpha=float(state['alpha'])
    for index,module in enumerate(enabled(definition,'operators')):
        p=module['parameters'];name=module['function']
        if name=='Remap Scalar':
            if p.get('output field') in (3,5,10):continue
            if p.get('output field')!=7 or p.get('input field') not in (1,7,8):
                raise ValueError('Unsupported ordered alpha remap field')
            value={1:lifetime,7:alpha,8:state['creation_simulation_time']}[p['input field']]
            alpha=remap(p,value,alpha)
        elif name=='Alpha Fade and Decay':
            incoming=fraction(age/lifetime,float(p.get('start_fade_in_time',0)),float(p.get('end_fade_in_time',.5)))
            outgoing=fraction(age/lifetime,float(p.get('start_fade_out_time',.5)),float(p.get('end_fade_out_time',1)))
            alpha*=float(p.get('start_alpha',1))+(1-float(p.get('start_alpha',1)))*incoming
            alpha*=1+(float(p.get('end_alpha',0))-1)*outgoing
        elif name=='Oscillate Scalar Simple' and int(p.get('oscillation field',7))==7:
            from particle_oscillation import delta
            alpha=min(1.,max(0.,alpha+delta(p,age)))
        elif name in ('Alpha Fade In Simple','Alpha Fade Out Simple'):
            from particle_bake import simple_fade_value
            alpha=simple_fade_value(name,p,age/lifetime,alpha,float(state['alpha']))
        elif name in ('Alpha Fade In Random','Alpha Fade Out Random'):
            single={**definition,'modules':{**definition['modules'],'operators':[module]}}
            durations={0:fade_durations[index]} if fade_durations is not None and index in fade_durations else None
            alpha*=appearance(single,age,lifetime,1.,durations)[1]
    return min(1.,max(0.,alpha))
