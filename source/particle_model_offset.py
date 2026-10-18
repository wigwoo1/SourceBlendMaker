"""Pass-two spawn offset shifts both positions without changing velocity."""
import math
def apply(position,previous,offset):
    if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in (position,previous,offset)):
        raise ValueError('Invalid model particle spawn offset')
    return tuple(a+b for a,b in zip(position,offset)),tuple(a+b for a,b in zip(previous,offset))
