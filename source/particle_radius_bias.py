"""Radius interpolation decoded from installed PET Radius Scale branches."""
import math

def interpolate(fraction,bias=.5,ease=False):
    fraction,bias=float(fraction),float(bias)
    if not math.isfinite(fraction) or not math.isfinite(bias) or not 0<=bias<=1:
        raise ValueError('Invalid particle radius bias')
    fraction=min(1.,max(0.,fraction))
    if ease:return fraction*fraction*(3-2*fraction)
    # PET OnUnpack replaces exactly zero with its neutral .5 default.
    if bias==0:bias=.5
    if fraction==0:return 0.
    if fraction==1:return 1.
    return fraction/(1+(1/bias-2)*(1-fraction))
