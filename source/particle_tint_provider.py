"""Birth-time scene binding for supplied lighting, with collection history.

The query and control-position callbacks are explicit dependencies. Engine
call-end sampling, SFM lighting settings and dynamic styles remain unverified.
No default worker provider is enabled by this module.
"""
import hashlib,json,math
from particle_tint_cache import CollectionColor,InitializerCache,History
from particle_tint_color import validate

class SceneTintProvider:
    def __init__(self,definitions,control_position,light_query,*,scale=.0254,context_position):
        if not math.isfinite(scale) or scale<=0:raise ValueError('Positive finite Source scale required')
        self.scale=scale;self.control_position=control_position;self.light_query=light_query
        self.context_position=InitializerCache.position(context_position)
        self.definitions={}
        for definition in definitions:
            identity=definition.get('instance_id')
            if type(identity) is not int or identity in self.definitions:
                raise ValueError('Unique integer particle graph instance IDs required')
            self.definitions[identity]=definition
        for definition in definitions:
            parent=definition.get('parent_instance_id')
            if parent is not None and parent not in self.definitions:
                raise ValueError('Tint parent graph instance is missing')
            visited=set();current=definition['instance_id']
            while current is not None:
                if current in visited:raise ValueError('Cyclic particle tint parent graph')
                visited.add(current);current=self.definitions[current].get('parent_instance_id')
        self.collections={i:CollectionColor() for i in self.definitions}
        self.histories={i:History() for i in self.definitions}
        self.caches={};self.query_records=[];self.parent_reads=[]

    def __call__(self,definition,parameters,shot_time,simulation_time):
        validate(parameters)
        if not all(math.isfinite(v) for v in (shot_time,simulation_time)):
            raise ValueError('Finite tint birth times required')
        identity=definition.get('instance_id')
        if identity not in self.definitions:raise ValueError('Unknown tint graph instance')
        if definition.get('parent_instance_id')!=self.definitions[identity].get('parent_instance_id'):
            raise ValueError('Tint parent instance changed during bake')
        history=self.histories[identity]
        if history.times and shot_time<history.times[-1]:
            raise ValueError('Tint births must be chronological within a collection')
        cp=int(parameters.get('tint control point',0))
        position=tuple(float(v)/self.scale for v in self.control_position(cp,shot_time))
        position=InitializerCache.position(position)
        signature=hashlib.sha256(json.dumps(parameters,sort_keys=True).encode()).hexdigest()
        key=(identity,signature)
        if key not in self.caches:
            self.caches[key]=InitializerCache(self.collections[identity],cp,
                float(parameters.get('tint update movement threshold',32.)),None,context_position=self.context_position)
        cache=self.caches[key]
        def query(point):
            packed=InitializerCache.bytes(self.light_query(cp,point,shot_time))
            self.query_records.append(dict(instance=identity,control_point=cp,time=shot_time,point=point,packed=packed))
            return packed
        cache.query=query
        parent_id=definition.get('parent_instance_id')
        parent=None if parent_id is None else self.histories[parent_id].at(shot_time)
        if parent is not None and parent.marker==cp:
            self.parent_reads.append(dict(instance=identity,parent=parent_id,time=shot_time))
        packed=cache.sample(position,parent=parent)
        history.record(shot_time,self.collections[identity])
        return packed
