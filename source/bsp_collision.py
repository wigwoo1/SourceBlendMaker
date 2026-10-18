"""Read Source brush collision planes without substituting render triangles.

Layout: Valve Source SDK public/bspfile.h. Trace simulation is not enabled yet.
Displacement and model collision geometry must be supplied separately.
"""
import struct
import math


def read_brushes(raw):
    if len(raw)<1036 or raw[:4]!=b'VBSP':raise ValueError('Invalid Source BSP collision header')
    version=struct.unpack_from('<i',raw,4)[0]
    if version not in (19,20,21):raise ValueError('Unsupported BSP collision version')
    def lump(index,stride):
        offset,length,revision,compressed=struct.unpack_from('<4i',raw,8+16*index)
        if revision!=0:raise ValueError('Unsupported collision lump revision')
        if offset<0 or length<0 or offset+length>len(raw):raise ValueError('Collision lump outside BSP')
        if compressed or raw[offset:offset+4]==b'LZMA':raise ValueError('Compressed collision lump requires decoding')
        if length%stride:raise ValueError('Misaligned collision lump')
        return raw[offset:offset+length]
    planes=list(struct.iter_unpack('<4fi',lump(1,20)))
    sides=list(struct.iter_unpack('<Hhhh',lump(19,8)))
    brushes=list(struct.iter_unpack('<iii',lump(18,12)))
    for plane in planes:
        if not all(math.isfinite(v) for v in plane[:4]) or sum(v*v for v in plane[:3])<1e-12:
            raise ValueError('Invalid BSP collision plane')
    result=[]
    for index,(first,count,contents) in enumerate(brushes):
        if first<0 or count<0 or first+count>len(sides):raise ValueError('Invalid BSP collision brush side range')
        selected=[]
        for plane,texture,displacement,bevel in sides[first:first+count]:
            if plane>=len(planes):raise ValueError('Invalid BSP collision plane index')
            selected.append({'normal':planes[plane][:3],'distance':planes[plane][3],
                             'texture_info':texture,'displacement':displacement,'bevel':bool(bevel)})
        result.append({'index':index,'contents':contents,'sides':selected})
    return {'version':version,'brushes':result,'plane_count':len(planes),
            'scope':'Brush geometry only; displacements, transformed submodels and MDL collision are not resolved'}


def read_world_brushes(raw):
    geometry=read_brushes(raw)
    def lump(index,stride,versions=(0,)):
        offset,length,revision,compressed=struct.unpack_from('<4i',raw,8+16*index)
        if revision not in versions:raise ValueError('Unsupported world collision lump revision')
        if offset<0 or length<0 or offset+length>len(raw):raise ValueError('World collision lump outside BSP')
        if compressed or raw[offset:offset+4]==b'LZMA':raise ValueError('Compressed world collision lump requires decoding')
        if length%stride:raise ValueError('Misaligned world collision lump')
        return raw[offset:offset+length]
    models=list(struct.iter_unpack('<9f3i',lump(14,48)))
    if not models:raise ValueError('Missing BSP world model')
    nodes=list(struct.iter_unpack('<3i6h2H2h',lump(5,32)))
    leaf_revision=struct.unpack_from('<i',raw,8+16*10+8)[0]
    leaves=lump(10,56 if leaf_revision==0 else 32,(0,1))
    leaf_size=56 if leaf_revision==0 else 32
    references=list(struct.iter_unpack('<H',lump(17,2)))
    selected=set();visited=set();pending=[models[0][9]]
    while pending:
        index=pending.pop()
        if index>=0:
            if index>=len(nodes):raise ValueError('Invalid world collision node index')
            if index in visited:raise ValueError('Repeated/cyclic world collision node')
            visited.add(index);pending.extend(nodes[index][1:3])
        else:
            leaf=-index-1
            if leaf>=len(leaves)//leaf_size:raise ValueError('Invalid world collision leaf index')
            first,count=struct.unpack_from('<2H',leaves,leaf*leaf_size+24)
            if first+count>len(references):raise ValueError('Invalid world leaf brush range')
            for ref in references[first:first+count]:
                if ref[0]>=len(geometry['brushes']):raise ValueError('Invalid world brush reference')
                selected.add(ref[0])
    return {**geometry,'brushes':[geometry['brushes'][i] for i in sorted(selected)],
            'all_brush_count':len(geometry['brushes']),'world_node_count':len(visited),
            'scope':'World BSP brushes only; displacements, brush entities and MDL collision remain separate'}
