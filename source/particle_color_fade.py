"""Installed Color Fade defaults and interpolation; color-space parity pending."""
import math

def settings(parameters):
    p={'fade_start_time':0.,'fade_end_time':1.,'ease_in_and_out':True,'output field':6,**parameters}
    if float(p['output field'])!=6:raise ValueError('Color Fade supports only RGB output field 6')
    for key in ('fade_start_time','fade_end_time'):
        p[key]=float(p[key])
        if not math.isfinite(p[key]):raise ValueError('Nonfinite Color Fade time')
    return p

def color(initial,target,fraction,parameters,current=None):
    p=settings(parameters)
    a,b=p['fade_start_time'],p['fade_end_time']
    # Installed operator returns without writes for equal endpoints.
    if a==b:return tuple(initial if current is None else current)
    amount=max(0.,min(1.,(float(fraction)-a)/(b-a)))
    if p['ease_in_and_out']:amount=amount*amount*(3-2*amount)
    return tuple(x+(y-x)*amount for x,y in zip(initial,target))
