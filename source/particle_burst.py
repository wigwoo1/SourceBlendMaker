"""Burst limits; Source simulation tick scheduling remains approximate."""
def validate_instantaneous_count(count,maximum):
    count,maximum=int(count),int(maximum)
    if count<0 or count>1000000:raise ValueError('Invalid burst particle count')
    if maximum < -1:raise ValueError('Invalid maximum emission per frame')
    if maximum!=-1 and count>maximum:raise ValueError('Multi-frame burst spreading is unsupported')
    return count
