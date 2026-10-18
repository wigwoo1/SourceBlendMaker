"""Experimental world convex-brush ray with texinfo flags; no engine epsilon.

Props, displacement surfaces and transformed submodels remain absent. Missing
hit surface metadata and start-solid results are explicitly rejected.
"""
import struct
from particle_brush_trace import sweep
from bsp_collision import read_world_brushes

class SkyBrushTrace:
    def __init__(self,brushes,texture_flags):
        self.brushes=brushes;self.flags=texture_flags

    @classmethod
    def from_bsp(cls,raw):
        brushes=read_world_brushes(raw)['brushes']
        at,size,revision,compressed=struct.unpack_from('<4i',raw,8+16*6)
        if at<0 or size<0 or at+size>len(raw) or revision!=0 or compressed or size%72:
            raise ValueError('Invalid sky texinfo lump')
        if raw[at:at+4]==b'LZMA':raise ValueError('Compressed sky texinfo')
        flags=[struct.unpack_from('<i',raw,index+64)[0] for index in range(at,at+size,72)]
        return cls(brushes,flags)

    def __call__(self,start,end,mask):
        closest=None;selected=None
        for brush in self.brushes:
            if not brush['contents']&mask:continue
            hit=sweep(start,end,brush['sides'],0.)
            if hit is not None and (closest is None or hit['fraction']<closest['fraction']):
                closest=hit;selected=brush
        if closest is None:return {'fraction':1.,'surface_flags':0,'hit':False}
        if closest['start_solid']:raise ValueError('Start-solid sky surface resolution unimplemented')
        for side in selected['sides']:
            normal=tuple(side['normal'])
            if normal!=closest['normal']:continue
            a=sum(n*v for n,v in zip(normal,start))-side['distance']
            b=sum(n*v for n,v in zip(normal,end))-side['distance']
            if a<=b or a/(a-b)!=closest['fraction']:continue
            texture=side['texture_info']
            if not 0<=texture<len(self.flags):raise ValueError('Missing sky hit texinfo metadata')
            return {**closest,'surface_flags':self.flags[texture],'hit':True,
                    'brush_index':selected['index'],'texture_info':texture}
        raise ValueError('Sky hit plane metadata could not be resolved')
