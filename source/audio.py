"""Timing-independent envelopes for imported Source sound clips."""


def envelope(elapsed,duration,fade_in=0.,fade_out=0.,volume=1.):
    if elapsed<0 or elapsed>duration:return 0.
    weight=1.
    if fade_in>0:weight=min(weight,max(0.,elapsed/fade_in))
    if fade_out>0:weight=min(weight,max(0.,(duration-elapsed)/fade_out))
    return max(0.,float(volume))*weight
