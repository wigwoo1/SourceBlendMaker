"""Experimental static BSP lighting for the tint provider.

Displacement/prop occlusion, dynamic lightstyles and Source spatial cache
cadence are absent. Unsupported cases fail explicitly instead of losing tint.
"""
import math
from particle_tint_lighting.map_light_visibility import MapLightVisibility
from particle_tint_lighting.sky_brush_trace import SkyBrushTrace
from particle_tint_lighting.pregather_rgb import cached_rgb
from particle_brush_trace import PreparedBrushTracer

class MapTintQuery:
    def __init__(self,raw,*,hdr,baked_ambient,radius_multiplier,style_value,minimum_brightness,capacity):
        if type(hdr) is not bool or type(baked_ambient) is not bool:
            raise ValueError('Explicit HDR and ambient policies required')
        if not all(math.isfinite(v) and v>=0 for v in (radius_multiplier,style_value,minimum_brightness)):
            raise ValueError('Finite nonnegative tint lighting settings required')
        if type(style_value) is not int:
            raise ValueError('Explicit integer runtime lightstyle required')
        if type(capacity) is not int or not 1<=capacity<=8:
            raise ValueError('Explicit checked tint light capacity required')
        self.provider=MapLightVisibility(raw,hdr)
        self.sky=SkyBrushTrace.from_bsp(raw)
        self.tracer=PreparedBrushTracer(self.sky.brushes,0x4481)
        self.settings=dict(baked_ambient=baked_ambient,radius_multiplier=radius_multiplier,
                           style_value=style_value,minimum_brightness=minimum_brightness,capacity=capacity)
        self.query_count=0
    def trace(self,start,end,mask):
        if mask!=0x4481:raise ValueError('Unsupported tint trace mask')
        return self.tracer(start,end,radius=0.) or dict(fraction=1.,start_solid=False)
    def __call__(self,control_point,position,shot_time):
        lights=self.provider.candidates(position)
        if any(light['style']!=0 for light in lights):
            raise ValueError('Dynamic map lightstyles for particle tint are unverified')
        result=cached_rgb(self.provider.ambient.cube(position),lights,position,self.trace,
                          sky_trace=self.sky,**self.settings)
        if result['first_pass']['other_emit_ids']:
            raise ValueError('Unsupported BSP light emission types for particle tint')
        self.query_count+=1
        return result['final']['packed_rgb']
