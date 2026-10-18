"""Immutable model-particle snapshots, independent of render query order.

The caller supplies simulation steps and complete operator updates. Linear
interpolation between snapshots is a converter approximation, not Source parity.
"""
import bisect,math

class History:
    def __init__(self):self.times=[];self.snapshots=[]
    def record(self,age,position,previous_position):
        if not math.isfinite(age) or age<0:raise ValueError('Finite nonnegative snapshot age required')
        if self.times and age<=self.times[-1]:raise ValueError('Model particle snapshots must be strictly chronological')
        vectors=tuple(tuple(float(x) for x in v) for v in (position,previous_position))
        if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vectors):raise ValueError('Finite snapshot positions required')
        self.times.append(age);self.snapshots.append(vectors)
    def query(self,age):
        if not math.isfinite(age) or not self.times or age<self.times[0] or age>self.times[-1]:raise ValueError('Query outside recorded model particle history')
        index=bisect.bisect_right(self.times,age)-1
        if self.times[index]==age:return self.snapshots[index]
        amount=(age-self.times[index])/(self.times[index+1]-self.times[index])
        return tuple(tuple(a+(b-a)*amount for a,b in zip(start,end)) for start,end in zip(self.snapshots[index],self.snapshots[index+1]))
