"""Experimental diagnostic composition, not a full Source light query.

No spatial cache, cache bounds, surface/sky calculation, renderer basis, cube
folding or final RGB output. Runtime style/capacity/threshold are explicit.
"""
from particle_tint_lighting.map_local_light import local_input
from particle_tint_lighting.light_brightness_gate import apply
from particle_tint_lighting.worldlight_visibility import rank_score
from particle_tint_lighting.light_selection import select_stream
from particle_tint_lighting.point_light import f32
from particle_tint_lighting.sky_light import query as sky_query

def diagnose(lights,point,*,style_value,minimum_brightness,capacity,ignore_radius,
             sky_trace=None):
    eligible=[];details=[];other=[]
    for light in lights:
        if light['type']==3 and sky_trace is not None:
            sky=sky_query(point,light['normal'],sky_trace)
            value={'incoming':sky['incoming'],'distance_attenuation':sky['attenuation'],
                   'cone':1.,'sky_query':sky}
            # Installed sky branch returns 1/0 directly, bypassing ordinary
            # style and max-channel brightness gating (0x1019462d..101947a4).
            gate={'accepted':sky['visible'],'attenuation':sky['attenuation']}
        elif light['type'] not in (0,1,2):
            other.append(light['index']);continue
        else:
            value=local_input(light,point,ignore_radius=ignore_radius)
            gate=apply(light['intensity'],value['distance_attenuation'],style_value=style_value,
                       minimum_brightness=0. if light['type']==0 else minimum_brightness)
        detail={'index':light['index'],**value,'gate':gate}
        if gate['accepted']:
            score=rank_score(light['intensity'],gate['attenuation'])
            detail['rank_score']=score
            # The selector has an additional luminance threshold; below it the
            # contribution is folded instead. Report separately, never discard.
            detail['selection_threshold_passed']=light['type']==0 or score>=f32(minimum_brightness)
            eligible.append((light['index'],score,detail['selection_threshold_passed']))
        details.append(detail)
    reduction=select_stream(eligible,capacity)
    return {'local_inputs':details,'ordered_slots':reduction,
            'other_emit_types_unimplemented':other,'complete_query':False}
