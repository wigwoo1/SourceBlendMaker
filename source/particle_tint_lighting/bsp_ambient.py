"""Experimental BSP ambient-only provider, using explicit HDR/LDR selection.

No world-light additions, lightstyles or engine spatial cache are reproduced.
Schema follows Valve public/bspfile.h; only version-1 separate ambient lumps.
"""
import math
import struct
from particle_tint_lighting.leaf_ambient import interpolate
from particle_tint_lighting.point_light import f32

class Ambient:
    def __init__(self, raw, hdr=True):
        if len(raw)<1036 or raw[:4]!=b'VBSP' or struct.unpack_from('<i',raw,4)[0] not in (19,20,21):
            raise ValueError('Unsupported BSP header')
        def lump(index,stride,revision):
            at,size,version,compressed=struct.unpack_from('<4i',raw,8+16*index)
            if version!=revision or at<0 or size<0 or at+size>len(raw):
                raise ValueError('Invalid ambient BSP lump')
            data=raw[at:at+size]
            if compressed or data[:4]==b'LZMA' or size%stride:
                raise ValueError('Compressed or misaligned ambient BSP lump')
            return data
        self.planes=list(struct.iter_unpack('<4fi',lump(1,20,0)))
        self.nodes=list(struct.iter_unpack('<3i6h2H2h',lump(5,32,0)))
        models=list(struct.iter_unpack('<9f3i',lump(14,48,0)))
        if not models:raise ValueError('No BSP world model')
        self.root=models[0][9]
        leaf_data=lump(10,32,1)
        self.bounds=[struct.unpack_from('<6h',leaf_data,at+8) for at in range(0,len(leaf_data),32)]
        self.indexes=list(struct.iter_unpack('<2H',lump(51 if hdr else 52,4,0)))
        sample_data=lump(55 if hdr else 56,28,1)
        self.samples=[sample_data[at:at+28] for at in range(0,len(sample_data),28)]
        if len(self.indexes)!=len(self.bounds):raise ValueError('Ambient index/leaf count mismatch')
        for values in self.bounds:
            if any(values[i]>values[i+3] for i in range(3)):raise ValueError('Inverted leaf bounds')
        for count,first in self.indexes:
            if count and first+count>len(self.samples):raise ValueError('Ambient sample range invalid')
            if not count and first and first>=len(self.bounds):raise ValueError('Ambient leaf alias invalid')
        for plane in self.planes:
            if any(not math.isfinite(v) for v in plane[:4]):raise ValueError('Nonfinite BSP plane')
        self.mode='HDR' if hdr else 'LDR'

    def leaf(self, point):
        if len(point)!=3 or any(not math.isfinite(v) for v in point):raise ValueError('Invalid sample point')
        point=tuple(f32(v) for v in point);node=self.root;seen=set()
        while node>=0:
            if node>=len(self.nodes) or node in seen:raise ValueError('Invalid or cyclic BSP tree')
            seen.add(node);entry=self.nodes[node]
            if not 0<=entry[0]<len(self.planes):raise ValueError('Invalid BSP plane index')
            plane=self.planes[entry[0]]
            distance=f32(f32(f32(point[0]*plane[0])+f32(point[1]*plane[1]))+f32(point[2]*plane[2]))
            node=entry[1 if distance>=plane[3] else 2]
        index=-node-1
        if index>=len(self.bounds):raise ValueError('Invalid BSP leaf index')
        return index

    def cube(self, point):
        leaf=self.leaf(point);count,first=self.indexes[leaf]
        if not count and first:
            leaf=first;count,first=self.indexes[leaf]
        bounds=self.bounds[leaf]
        center=[f32((bounds[i]+bounds[i+3])*.5) for i in range(3)]
        half=[f32((bounds[i+3]-bounds[i])*.5) for i in range(3)]
        return interpolate(self.samples[first:first+count],center,half,point)
