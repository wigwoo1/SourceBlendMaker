"""Experimental cached cube plus selected-light diagnostic, not engine parity.

Displaced sky lights have zero incoming direction in the inspected first-pass
branch. Other displaced lights recover attenuation from stored rank/luminance.
Dynamic styles, cache lifetime and exact normalize/angle parity remain absent.
"""
from particle_tint_lighting.point_pregather import gather
from particle_tint_lighting.worldlight_visibility import rank_score
from particle_tint_lighting.worldlight_cube import add
from particle_tint_lighting.local_lighting_rgb import BASIS,diagnostic_rgb
from particle_tint_lighting.point_light import f32

def cached_rgb(cube,lights,point,trace,*,baked_ambient,radius_multiplier,
               style_value,minimum_brightness,capacity,sky_trace=None):
    first=gather(lights,point,trace,baked_ambient=baked_ambient,
        radius_multiplier=radius_multiplier,style_value=style_value,
        minimum_brightness=minimum_brightness,capacity=capacity,sky_trace=sky_trace)
    by_id={light['index']:light for light in lights}
    if len(by_id)!=len(lights):raise ValueError('Duplicate world-light IDs')
    details={item['index']:item for item in first['details']}
    folded_cube=[list(face) for face in cube]
    for event in first['slots']['fold_events']:
        index,stored_score=event['candidate'];light=by_id[index];item=details[index]
        incoming=item['incoming'];attenuation=item['gate']['attenuation']
        if event['kind']=='displaced':
            if light['type']==3:
                incoming=(0.,0.,0.);attenuation=1.
            else:
                luminance=rank_score(light['intensity'],1.)
                if luminance<=0:raise ValueError('Displaced-light luminance division unresolved')
                attenuation=f32(stored_score/luminance)
        folded_cube=add(folded_cube,BASIS,incoming,light['intensity'],
                        f32(attenuation*item['cone']))
    selected=[by_id[index] for index,_ in first['slots']['selected']]
    second=diagnostic_rgb(folded_cube,selected,point,style_value=style_value,
        minimum_brightness=minimum_brightness,capacity=capacity,
        baked_ambient=False,sky_trace=sky_trace)
    return dict(first_pass=first,cached_cube=folded_cube,final=second,
                complete_query=False,source_runtime_comparison=False,production_enabled=False)
