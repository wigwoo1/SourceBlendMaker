"""Cache identity matching Blender's integer frame and float32 subframe."""
import math,struct

def cache_key(cp,time,shot_start,fps):
    frame=1+(time-shot_start)*fps
    whole=math.floor(frame)
    subframe=struct.unpack('<f',struct.pack('<f',frame-whole))[0]
    return cp,whole,subframe
