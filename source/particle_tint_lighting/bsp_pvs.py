"""Experimental bounded visibility-lump reader; no live area-portal state."""
import struct

class Visibility:
    def __init__(self, data):
        self.data=bytes(data)
        if len(data)<4:raise ValueError('Missing visibility header')
        self.count=struct.unpack_from('<i',data)[0]
        if self.count<0 or 4+8*self.count>len(data):raise ValueError('Invalid cluster table')
        self.offsets=list(struct.iter_unpack('<2i',data[4:4+8*self.count]))
        self.row_bytes=(self.count+7)//8
        self.cache={}

    def row(self, cluster):
        if type(cluster) is not int or not 0<=cluster<self.count:
            raise ValueError('Invalid source cluster')
        if cluster in self.cache:return self.cache[cluster]
        at=self.offsets[cluster][0]; output=bytearray()
        if at<4+8*self.count or at>=len(self.data):
            raise ValueError('Invalid PVS stream offset')
        while len(output)<self.row_bytes:
            if at>=len(self.data):raise ValueError('Truncated PVS stream')
            value=self.data[at];at+=1
            if value:output.append(value)
            else:
                if at>=len(self.data):raise ValueError('Truncated PVS zero run')
                count=self.data[at];at+=1
                if count==0 or len(output)+count>self.row_bytes:
                    raise ValueError('Invalid PVS zero run')
                output.extend(bytes(count))
        result=bytes(output);self.cache[cluster]=result
        return result

    def visible(self, source_cluster, target_cluster):
        if type(target_cluster) is not int or not 0<=target_cluster<self.count:
            raise ValueError('Invalid target cluster')
        row=self.row(source_cluster)
        return bool(row[target_cluster>>3] & (1<<(target_cluster&7)))
