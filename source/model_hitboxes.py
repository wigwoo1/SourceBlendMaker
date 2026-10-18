"""Read Source MDL bone-local hitboxes; no particle sampling policy is implied.

Layout reference: ValveSoftware/source-sdk-2013 src/public/studio.h.
Only the classic 68-byte bounding-box layout used by MDL 44 through 49 is read.
"""
import math,struct

def read(raw):
    raw=bytes(raw)
    def span(offset,size):
        if offset<0 or size<0 or offset+size>len(raw):raise ValueError('Hitbox data outside MDL bounds')
    def string(base,relative):
        if relative==0:return ''
        offset=base+relative;span(offset,1)
        end=raw.find(b'\0',offset)
        if end<0:raise ValueError('Unterminated hitbox name')
        return raw[offset:end].decode('utf-8',errors='replace')
    span(0,180)
    if raw[:4]!=b'IDST':raise ValueError('Source MDL signature required')
    version=struct.unpack_from('<i',raw,4)[0]
    if version not in range(44,50):raise ValueError('Unsupported MDL hitbox layout')
    length=struct.unpack_from('<i',raw,76)[0]
    if length!=len(raw):raise ValueError('MDL declared length differs from buffer')
    bones=struct.unpack_from('<i',raw,156)[0]
    count,offset=struct.unpack_from('<ii',raw,172)
    if bones<0 or count<0:raise ValueError('Negative MDL bone or hitbox-set count')
    span(offset,count*12)
    sets=[]
    for index in range(count):
        base=offset+index*12
        name_offset,box_count,box_offset=struct.unpack_from('<iii',raw,base)
        if box_count<0:raise ValueError('Negative hitbox count')
        start=base+box_offset;span(start,box_count*68)
        boxes=[]
        for box_index in range(box_count):
            pos=start+box_index*68
            bone,group,*values=struct.unpack_from('<ii6fi',raw,pos)
            minimum=values[:3];maximum=values[3:6];label=values[6]
            if not 0<=bone<bones:raise ValueError('Hitbox bone index outside model')
            if not all(math.isfinite(v) for v in minimum+maximum):raise ValueError('Nonfinite hitbox bounds')
            if any(a>b for a,b in zip(minimum,maximum)):raise ValueError('Inverted hitbox bounds')
            boxes.append(dict(bone=bone,group=group,minimum=minimum,maximum=maximum,name=string(pos,label)))
        sets.append(dict(name=string(base,name_offset),boxes=boxes))
    return dict(version=version,bone_count=bones,sets=sets)
