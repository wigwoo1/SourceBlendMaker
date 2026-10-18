"""Experimental diagnostic ambient + local lighting, not Source-query parity.

Selection/cache bounds and exact floating-point parity are incomplete. Unsupported
emit types remain explicit in the result. Never use as a production fallback.
"""
from particle_tint_lighting.local_lighting_pipeline import diagnose
from particle_tint_lighting.map_local_light import local_input
from particle_tint_lighting.light_brightness_gate import apply
from particle_tint_lighting.worldlight_cube import add
from particle_tint_lighting.point_light import color_bytes,f32
from particle_tint_lighting.sky_light import query as sky_query

# Verified installed VStudioRender026 slots 17/18 and vector table 0x1008a480.
BASIS=((1.,0.,0.),(-1.,0.,0.),(0.,1.,0.),(0.,-1.,0.),(0.,0.,1.),(0.,0.,-1.))

def diagnostic_rgb(ambient_cube,lights,point,*,style_value,minimum_brightness,capacity,
                   baked_ambient,sky_trace=None):
    if type(baked_ambient) is not bool:raise ValueError('Explicit baked ambient policy required')
    skipped=[light['index'] for light in lights if baked_ambient and light.get('flags',0)&1]
    filtered=[light for light in lights if light['index'] not in skipped]
    pipeline=diagnose(filtered,point,style_value=style_value,
        minimum_brightness=minimum_brightness,capacity=capacity,ignore_radius=True,
        sky_trace=sky_trace)
    by_id={light['index']:light for light in lights}
    if len(by_id)!=len(lights):raise ValueError('Duplicate world-light indices')
    details={item['index']:item for item in pipeline['local_inputs']}
    folded=[index for index,_ in pipeline['ordered_slots']['folded']]
    cube=[list(face) for face in ambient_cube]
    for index in folded:
        item=details[index];light=by_id[index]
        cube=add(cube,BASIS,item['incoming'],light['intensity'],
                 f32(item['gate']['attenuation']*item['cone']))
    for index,_ in pipeline['ordered_slots']['selected']:
        light=by_id[index]
        if light['type']==3:
            sky=sky_query(point,light['normal'],sky_trace)
            if sky['visible']:
                cube=add(cube,BASIS,sky['incoming'],light['intensity'],sky['attenuation'])
            continue
        # Final selected-light evaluation uses flag 1, retaining radius cutoff.
        item=local_input(light,point,ignore_radius=False)
        gate=apply(light['intensity'],item['distance_attenuation'],style_value=style_value,
                   minimum_brightness=0. if light['type']==0 else minimum_brightness)
        if gate['accepted']:
            cube=add(cube,BASIS,item['incoming'],light['intensity'],
                     f32(gate['attenuation']*item['cone']))
    return {'cube':cube,'packed_rgb':color_bytes(cube),'pipeline':pipeline,
            'already_baked_light_ids_skipped':skipped,
            'complete_query':False,'cache_implemented':False,'fold_event_order_preserved':True}
