"""Experimental world-light PVS gate; attenuation and engine caches are separate."""
import struct,math
from particle_tint_lighting.bsp_ambient import Ambient
from particle_tint_lighting.bsp_pvs import Visibility

def eligible(visibility, source_cluster, leaf_flags, light_cluster, emit_type):
    # Installed selector 0x10197363..0x101973a9 uses leaf sky flags for type 3.
    if emit_type==3:return bool(leaf_flags & 5)
    if light_cluster<0:return False
    if source_cluster<0:raise ValueError('Solid/outside leaf PVS policy not implemented')
    return visibility.visible(source_cluster,light_cluster)

class MapLightVisibility:
    def __init__(self, raw, hdr=True):
        self.ambient=Ambient(raw,hdr)
        def lump(index):
            at,size,revision,compressed=struct.unpack_from('<4i',raw,8+16*index)
            if at<0 or size<0 or at+size>len(raw) or compressed:
                raise ValueError('Invalid visibility/light lump')
            data=raw[at:at+size]
            if data[:4]==b'LZMA':raise ValueError('Compressed visibility/light lump')
            return data,revision
        data,revision=lump(4)
        if revision!=0:raise ValueError('Unknown visibility revision')
        self.visibility=Visibility(data)
        leaves,_=lump(10)
        self.leaves=[(struct.unpack_from('<h',leaves,at+4)[0],
                      struct.unpack_from('<H',leaves,at+6)[0]>>9)
                     for at in range(0,len(leaves),32)]
        data,revision=lump(54 if hdr else 15)
        version=struct.unpack_from('<i',raw,4)[0]
        stride=100 if version>20 else 88;shift=12 if version>20 else 0
        if revision not in (0,1) or len(data)%stride:raise ValueError('Invalid world-light layout')
        self.lights=[]
        for at in range(0,len(data),stride):
            cluster,emit,style=struct.unpack_from('<3i',data,at+36+shift)
            origin=struct.unpack_from('<3f',data,at)
            intensity=struct.unpack_from('<3f',data,at+12)
            normal=struct.unpack_from('<3f',data,at+24)
            parameters=struct.unpack_from('<7f',data,at+48+shift)
            if any(not math.isfinite(v) for v in (*origin,*intensity,*normal,*parameters)):
                raise ValueError('Nonfinite map light')
            self.lights.append({'index':at//stride,'cluster':cluster,'type':emit,'style':style,
                'origin':origin,'intensity':intensity,'normal':normal,
                **dict(zip(('inner','outer','exponent','radius','constant','linear','quadratic'),parameters)),
                'flags':struct.unpack_from('<i',data,at+76+shift)[0]})

    def candidates(self, point):
        leaf=self.ambient.leaf(point);cluster,flags=self.leaves[leaf]
        return [light for light in self.lights if eligible(self.visibility,cluster,flags,
                                                        light['cluster'],light['type'])]
