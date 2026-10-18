"""Experimental surface/point/spot/sky cache pregather diagnostic.

No cache hashing, dynamic styles, color folding or complete Source parity.
Trace callback must supply engine-like fraction and start-solid metadata.
"""
from particle_tint_lighting.cache_bounds import bounds
from particle_tint_lighting.light_bounds import point_eligible
from particle_tint_lighting.map_local_light import local_input
from particle_tint_lighting.light_brightness_gate import apply
from particle_tint_lighting.worldlight_visibility import point_visible,rank_score,TRACE_CONTENTS_MASK
from particle_tint_lighting.light_pregather_selection import select_stream
from particle_tint_lighting.point_light import f32
from particle_tint_lighting.light_cone_bounds import sphere_cone
from particle_tint_lighting.sky_light import query as sky_query
import math

def gather(lights,point,trace,*,baked_ambient,radius_multiplier,style_value,
           minimum_brightness,capacity,sky_trace=None):
    if type(baked_ambient) is not bool or not callable(trace):
        raise ValueError('Explicit ambient policy and trace callback required')
    low,high=bounds(point);details=[];candidates=[];other=[];skipped=[]
    for light in lights:
        if baked_ambient and light.get('flags',0)&1:
            skipped.append(light['index']);continue
        if light['type'] not in (0,1,2,3):
            other.append(light['index']);continue
        item=dict(index=light['index'])
        if light['type']==3:
            if sky_trace is None:
                other.append(light['index']);continue
            sky=sky_query(point,light['normal'],sky_trace)
            item['sky']=sky
            if not sky['visible']:
                item['rejected']='sky visibility';details.append(item);continue
            score=rank_score(light['intensity'],sky['attenuation'])
            item.update(incoming=sky['incoming'],cone=1.,rank_score=score,
                        gate=dict(attenuation=sky['attenuation'],accepted=True))
            candidates.append((light['index'],score,score>=f32(minimum_brightness)))
            details.append(item);continue
        if light['type'] in (0,2):
            cell_radius=f32(math.sqrt(sum(f32(f32(b)-f32(p))**2 for p,b in zip(point,high))))
            distance=f32(math.sqrt(sum(f32(f32(a)-f32(p))**2 for a,p in zip(light['origin'],point))))
            limit=f32(f32(light['radius']*(radius_multiplier if light['type']==2 else 1.))+cell_radius)
            if distance>limit:
                item['rejected']='sphere radius';details.append(item);continue
            cosine=light['outer'] if light['type']==2 else 0.
            if not -1<=cosine<=1:raise ValueError('Invalid outer cone cosine')
            sine=f32(math.sqrt(max(0.,1.-cosine*cosine))) if light['type']==2 else 1.
            if not sphere_cone(point,cell_radius,light['origin'],light['normal'],sine=sine,cosine=cosine):
                item['rejected']='cone bounds';details.append(item);continue
        if light['type'] in (1,2):
            item['bounds']=point_eligible(low,high,light['origin'],light['radius'],
                                         radius_multiplier=radius_multiplier)
            if not item['bounds']['eligible']:
                item['rejected']='bounds';details.append(item);continue
        value=local_input(light,point,ignore_radius=True)
        gate=apply(light['intensity'],value['distance_attenuation'],style_value=style_value,
                   minimum_brightness=0. if light['type']==0 else minimum_brightness)
        item.update(value);item['gate']=gate
        if not gate['accepted'] or gate['attenuation']<=0:
            item['rejected']='attenuation';details.append(item);continue
        hit=trace(point,light['origin'],TRACE_CONTENTS_MASK)
        if not isinstance(hit,dict) or 'fraction' not in hit or 'start_solid' not in hit:
            raise ValueError('Explicit trace fraction and start-solid metadata required')
        if hit['start_solid']:raise ValueError('Start-solid pregather trace semantics unresolved')
        # local_input's normalization uses this source-to-point distance.
        length=math.sqrt(sum((f32(f32(a)-f32(b)))**2 for a,b in zip(light['origin'],point)))
        item['trace']=hit
        if not point_visible(hit['fraction'],length):
            item['rejected']='visibility';details.append(item);continue
        score=rank_score(light['intensity'],gate['attenuation'])
        item['rank_score']=score
        candidates.append((light['index'],score,light['type']==0 or score>=f32(minimum_brightness)))
        details.append(item)
    return dict(low=low,high=high,details=details,slots=select_stream(candidates,capacity),
                other_emit_ids=other,baked_ids_skipped=skipped,complete_gather=False)
