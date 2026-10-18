"""Read Source BSP leaves to separate a 3D sky area from playable geometry."""
from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class Leaf:
    contents:int
    cluster:int
    area:int
    flags:int
    first_face:int
    face_count:int

def read_leaves(data,version):
    size={0:56,1:32}.get(version)
    if size is None:raise ValueError(f'Unsupported BSP leaf version {version}')
    if len(data)%size:raise ValueError('Truncated BSP leaf lump')
    result=[]
    for offset in range(0,len(data),size):
        contents,cluster,bits=struct.unpack_from('<ihH',data,offset)
        first,count=struct.unpack_from('<HH',data,offset+20)
        result.append(Leaf(contents,cluster,bits&511,bits>>9,first,count))
    return result

def classify(bsp,camera):
    """Find the camera's leaf through splitting planes, then its area faces."""
    def lump_bytes(index):
        info=bsp.info.lumps[index]
        buf=bsp._get_lump_buffer(index,info)
        return buf.read(),info.version
    raw,version=lump_bytes(10);leaves=read_leaves(raw,version)
    raw,_=lump_bytes(16)
    if len(raw)%2:raise ValueError('Truncated BSP leaf-face indices')
    indices=struct.unpack('<'+'H'*(len(raw)//2),raw)
    planes=bsp.get_lump('LUMP_PLANES').planes
    nodes=bsp.get_lump('LUMP_NODES').nodes
    point=tuple(float(v) for v in camera['origin'].split())
    node_index=0;seen=set()
    while node_index>=0:
        if node_index in seen:raise ValueError('Cyclic BSP tree')
        seen.add(node_index)
        node=nodes[node_index];plane=planes[node.plane_index]
        distance=sum(a*b for a,b in zip(point,plane.normal))-plane.dist
        node_index=node.childes_id[0 if distance>=0 else 1]
    leaf_index=-node_index-1;camera_leaf=leaves[leaf_index]
    if camera_leaf.contents&1:raise ValueError('Sky camera is inside a solid leaf')
    sky_faces=set();other_faces=set();area_leaf_count=0
    for leaf in leaves:
        if leaf.first_face+leaf.face_count>len(indices):raise ValueError('Invalid BSP leaf-face range')
        if leaf.contents&1:continue
        faces=indices[leaf.first_face:leaf.first_face+leaf.face_count]
        if leaf.area==camera_leaf.area:
            sky_faces.update(faces);area_leaf_count+=1
        else:other_faces.update(faces)
    shared=sky_faces&other_faces
    return {'camera_leaf':leaf_index,'area':camera_leaf.area,'leaf_count':len(leaves),
            'sky_area_leaves':area_leaf_count,'sky_faces':sorted(sky_faces-other_faces),
            'shared_faces':sorted(shared),'scale':float(camera.get('scale',16))}

def point_area(bsp,point):
    """Classify a prop origin using the same BSP split planes as the camera."""
    leaves=getattr(bsp,'_sfm_sky_leaves',None)
    if leaves is None:
        info=bsp.info.lumps[10]
        leaves=read_leaves(bsp._get_lump_buffer(10,info).read(),info.version)
        bsp._sfm_sky_leaves=leaves
    nodes=bsp.get_lump('LUMP_NODES').nodes;planes=bsp.get_lump('LUMP_PLANES').planes
    index=0;seen=set()
    while index>=0:
        if index in seen:raise ValueError('Cyclic BSP tree')
        seen.add(index)
        node=nodes[index];plane=planes[node.plane_index]
        front=sum(a*b for a,b in zip(point,plane.normal))>=plane.dist
        index=node.childes_id[0 if front else 1]
    leaf=leaves[-index-1]
    return None if leaf.contents&1 else leaf.area

def leaf_areas(bsp,indices):
    leaves=getattr(bsp,'_sfm_sky_leaves',None)
    if leaves is None:
        info=bsp.info.lumps[10]
        leaves=read_leaves(bsp._get_lump_buffer(10,info).read(),info.version)
        bsp._sfm_sky_leaves=leaves
    result=set()
    for index in indices:
        if not 0<=index<len(leaves):raise ValueError('Invalid static-prop leaf index')
        if not leaves[index].contents&1:result.add(leaves[index].area)
    return result
