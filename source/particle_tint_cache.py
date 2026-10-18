"""Initializer context plus collection-owned tint color for supplied lighting.

Matches scalar sharing/reuse branches at 0x10234b70..0x10234c53. Caller must
supply initialized context position and evaluated CP position; tick scheduling
and engine spatial lighting cache are outside this helper.
"""
import math
import struct
def f32(value):
    try:return struct.unpack('<f',struct.pack('<f',value))[0]
    except OverflowError:raise ValueError('Tint cache value overflows float32') from None

class CollectionColor:
    def __init__(self):self.marker=-1;self.color=None

class InitializerCache:
    def __init__(self,collection,control_point,threshold,query,*,context_position):
        if type(control_point) is not int or control_point<0:
            raise ValueError('Nonnegative integer control point required')
        if not math.isfinite(threshold) or threshold<0:raise ValueError('Invalid tint threshold')
        self.collection=collection;self.control_point=control_point;self.threshold=f32(threshold)
        self.query=query;self.context=self.position(context_position);self.query_count=0

    @staticmethod
    def position(value):
        if len(value)!=3 or any(not math.isfinite(v) for v in value):
            raise ValueError('Finite context position required')
        converted=tuple(map(f32,value))
        if not all(math.isfinite(v) for v in converted):raise ValueError('Float32 position overflow')
        return converted

    @staticmethod
    def bytes(value):
        value=tuple(value)
        if len(value)!=4 or any(type(v) is not int or not 0<=v<=255 for v in value):
            raise ValueError('Four valid collection color bytes required')
        return value

    def sample(self,position,*,parent=None):
        if parent is not None and parent.marker==self.control_point:
            return self.bytes(parent.color)
        position=self.position(position)
        delta=tuple(f32(a-b) for a,b in zip(self.context,position))
        squared=f32(f32(f32(delta[1]*delta[1])+f32(delta[2]*delta[2]))+f32(delta[0]*delta[0]))
        distance=f32(math.sqrt(squared))
        if distance<self.threshold and self.collection.marker!=-1:
            return self.bytes(self.collection.color)
        color=self.bytes(self.query(position))
        self.collection.marker=self.control_point;self.collection.color=color
        self.context=position;self.query_count+=1
        return color


import bisect,math


class History:
    def __init__(self):self.times=[];self.states=[]

    def record(self,time,collection):
        if not math.isfinite(time):raise ValueError('Finite timestamp required')
        if self.times and time<self.times[-1]:raise ValueError('Cache writes must be chronological')
        state=CollectionColor();state.marker=collection.marker
        state.color=None if collection.color is None else InitializerCache.bytes(collection.color)
        self.times.append(time);self.states.append(state)

    def at(self,time):
        if not math.isfinite(time):raise ValueError('Finite timestamp required')
        index=bisect.bisect_right(self.times,time)-1
        if index<0:return CollectionColor()
        stored=self.states[index]
        result=CollectionColor();result.marker=stored.marker;result.color=stored.color
        return result
