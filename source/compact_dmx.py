"""Read-only numeric DMX arrays retained in their original binary storage."""
import struct
from collections.abc import Sequence

class NumericArray(Sequence):
    def __init__(self,raw,format,converter):
        self.raw=raw;self.format='<'+format;self.converter=converter
        self.item_size=struct.calcsize(self.format)
        if len(raw)%self.item_size:raise ValueError('Truncated numeric DMX array')
    def __len__(self):return len(self.raw)//self.item_size
    def __getitem__(self,index):
        if isinstance(index,slice):return [self[i] for i in range(*index.indices(len(self)))]
        if index<0:index+=len(self)
        if not 0<=index<len(self):raise IndexError(index)
        return self.converter(struct.unpack_from(self.format,self.raw,index*self.item_size))
    def __iter__(self):
        return (self.converter(value) for value in struct.iter_unpack(self.format,self.raw))
