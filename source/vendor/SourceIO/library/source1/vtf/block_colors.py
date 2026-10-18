"""RGB565 endpoint expansion for static 2D VTF BC1/2/3 textures.

The bundled native decoder truncates RGB565 endpoint low bits. Decode RGB
from the original blocks instead; native alpha, float formats, animations and
cubemaps retain their existing path. Interpolation is integer BC arithmetic.
"""
import struct


def rgb(data):
    import numpy as np
    if len(data)<64 or data[:4]!=b'VTF\0':return None
    major,minor,header=struct.unpack_from('<III',data,4)
    if major!=7 or minor>5:return None
    width,height=struct.unpack_from('<HH',data,16)
    flags=struct.unpack_from('<I',data,20)[0]
    frames=struct.unpack_from('<H',data,24)[0]
    fmt=struct.unpack_from('<I',data,52)[0]
    if fmt not in (13,14,15,20) or frames!=1 or flags&0x4000:return None
    if minor>=2 and len(data)>=65 and struct.unpack_from('<H',data,63)[0]>1:return None
    mips=data[56]
    if not width or not height or not 1<=mips<=32 or header>len(data):
        raise ValueError('Invalid compressed VTF dimensions/header')
    block_size=8 if fmt in (13,20) else 16
    def size(w,h,block):return ((w+3)//4)*((h+3)//4)*block
    if minor>=3:
        if len(data)<80:raise ValueError('Truncated VTF resource table')
        count=struct.unpack_from('<I',data,68)[0]
        if count>4096 or 80+8*count>header:raise ValueError('Invalid VTF resource table')
        start=None
        for i in range(count):
            tag,resource_flags,offset=struct.unpack_from('<3sBI',data,80+8*i)
            if tag==b'\x30\0\0':
                if resource_flags&2:raise ValueError('Inline VTF image resource')
                start=offset
        if start is None:return None
    else:
        low_format=struct.unpack_from('<I',data,57)[0];lw,lh=data[61:63]
        if lw and lh:
            if low_format not in (13,14,15,20):return None
            low_size=size(lw,lh,8 if low_format in (13,20) else 16)
        else:low_size=0
        start=header+low_size
    start+=sum(size(max(1,width>>level),max(1,height>>level),block_size)
               for level in range(1,mips))
    length=size(width,height,block_size)
    if start<header or start+length>len(data):raise ValueError('Truncated VTF compressed image')
    blocks=np.frombuffer(data,dtype=np.uint8,count=length,offset=start).reshape(-1,block_size)
    colors=blocks[:,-8:]
    c0=colors[:,0].astype(np.uint32)|(colors[:,1].astype(np.uint32)<<8)
    c1=colors[:,2].astype(np.uint32)|(colors[:,3].astype(np.uint32)<<8)
    def expand(c):
        r=(c>>11)&31;g=(c>>5)&63;b=c&31
        return np.stack(((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2)),axis=1)
    a,b=expand(c0),expand(c1)
    palette=np.stack((a,b,(2*a+b)//3,(a+2*b)//3),axis=1)
    if fmt in (13,20):
        three=c0<=c1
        palette[three,2]=(a[three]+b[three])//2
        palette[three,3]=0
    indices=sum(colors[:,4+i].astype(np.uint32)<<(8*i) for i in range(4))
    selectors=(indices[:,None]>>(2*np.arange(16,dtype=np.uint32)))&3
    pixels=palette[np.arange(len(blocks))[:,None],selectors]
    bx=(width+3)//4;by=(height+3)//4
    return pixels.reshape(by,bx,4,4,3).transpose(0,2,1,3,4).reshape(by*4,bx*4,3)[:height,:width].astype(np.uint8)
