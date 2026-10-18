"""Validated reader for Source baked static-prop hardware vertex colors.

Colors are preserved as encoded RGBA8888, not mislabeled as linear light.
Source's vertex-light gamma/overbright conversion is a separate rendering step.
"""
from dataclasses import dataclass
import struct
import json
import numpy as np


@dataclass
class Mesh:
    lod:int
    rgba:np.ndarray


@dataclass
class Lighting:
    checksum:int
    meshes:list[Mesh]


def linear_colors(rgba):
    """Source PC vertex shader: GammaToLinear(encoded RGB * 2).

    Valve common_vs_fxc.h defines cOverbright=2; common_fxc.h uses
    pow(gamma,2.2), explicitly distinct from its sRGB conversion.
    Alpha is data and must not receive this lighting conversion.
    """
    result=np.asarray(rgba,dtype=np.float32)/255.
    result=result.copy()
    result[:,:3]=np.power(result[:,:3]*2.,2.2)
    return result


def model_colors(lighting, mesh_object):
    """Match a native model's vertex order; reject ambiguous/mismatched data."""
    checksum=int(mesh_object['sfm_vhv_checksum'])
    if checksum!=lighting.checksum:
        raise ValueError('VHV lighting belongs to a different model checksum')
    counts=json.loads(mesh_object['sfm_vhv_lod0_group_counts'])
    start=int(mesh_object['sfm_vhv_lod0_group_start'])
    groups=[mesh for mesh in lighting.meshes if mesh.lod==0]
    if start<0 or start+len(counts)>len(groups):
        raise ValueError('VHV does not contain this model strip-group range')
    selected=groups[start:start+len(counts)]
    if [len(mesh.rgba) for mesh in selected]!=counts:
        raise ValueError('VHV strip-group vertex counts do not match the model')
    if sum(counts)!=len(mesh_object.data.vertices):
        raise ValueError('Imported model vertex order cannot represent this VHV')
    return np.concatenate([mesh.rgba for mesh in selected],axis=0) if selected else np.empty((0,4),dtype=np.uint8)


def read(data,expected_checksum=None):
    if len(data)<40:raise ValueError('Truncated VHV header')
    version,checksum,flags,stride,vertices,mesh_count=struct.unpack_from('<6I',data)
    if version!=2:raise ValueError(f'Unsupported VHV version {version}')
    if flags!=4 or stride!=4:raise ValueError('Unsupported VHV vertex format')
    if expected_checksum is not None and checksum!=(int(expected_checksum)&0xffffffff):
        raise ValueError('VHV lighting belongs to a different model checksum')
    table_end=40+mesh_count*28
    if table_end>len(data):raise ValueError('Truncated VHV mesh table')
    meshes=[];ranges=[];total=0
    for index in range(mesh_count):
        lod,count,offset=struct.unpack_from('<3I',data,40+index*28)
        end=offset+count*stride
        if offset<table_end or end>len(data):raise ValueError('Invalid VHV vertex range')
        if any(offset<previous_end and previous_start<end for previous_start,previous_end in ranges):
            raise ValueError('Overlapping VHV vertex ranges')
        ranges.append((offset,end));total+=count
        bgra=np.frombuffer(data,dtype=np.uint8,count=count*4,offset=offset).reshape(count,4)
        meshes.append(Mesh(int(lod),bgra[:,[2,1,0,3]].copy()))
    if total!=vertices:raise ValueError('VHV total vertex count does not match its meshes')
    return Lighting(int(checksum),meshes)


def from_map(bsp,prop_index,hdr=True,expected_checksum=None):
    # Filenames repeat in every map. Read this BSP's own pak, never a global
    # content-manager mount that could return another map's prop lighting.
    from SourceIO.library.utils import TinyPath
    pak=bsp.get_lump('LUMP_PAK')
    for prefix in (('sp_hdr_','sp_') if hdr else ('sp_',)):
        name=f'{prefix}{int(prop_index)}.vhv'
        buffer=pak.find_file(TinyPath(name)) if pak else None
        if buffer is not None:
            buffer.seek(0)
            return name,read(buffer.read(),expected_checksum)
    return None,None
