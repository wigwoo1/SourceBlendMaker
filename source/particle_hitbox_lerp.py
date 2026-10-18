"""Hitbox target interpolation reconstructed from installed function 0x10279590.

Used by the animated model scene adapter. Source update cadence and hitbox
query dispatch parity remain unverified; callers supply the target explicitly.
"""
import math,struct

def f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]

def weight(age,start,end,strength):
    if not all(math.isfinite(v) for v in (age,start,end,strength)):raise ValueError('Finite hitbox lerp inputs required')
    if age<0 or end<=0 or start>=end:raise ValueError('Unsupported hitbox lerp time range')
    age,start,end,strength=map(f32,(age,start,end,strength))
    if age<=start or age>=end:return 0.
    reciprocal=f32(1./f32(end-start))
    return f32(f32(f32(age-start)*reciprocal)*strength)

def apply(position,previous_position,target,*,age,start=0.,end=1.,strength=1.):
    vectors=[tuple(v) for v in (position,previous_position,target)]
    if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vectors):raise ValueError('Finite three-component hitbox positions required')
    w=weight(age,start,end,strength)
    def blend(vector):
        return tuple(f32(f32(a)+f32(f32(f32(b)-f32(a))*w)) for a,b in zip(vector,vectors[2]))
    return blend(vectors[0]),blend(vectors[1])
