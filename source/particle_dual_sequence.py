"""Verified dual SpriteCard settings and per-particle texture samples."""
import math
from particle_sheet_table import Table
from particle_dual_sequence_uv import coordinates


def settings(material,renderer,function):
    if not material.get('sfm_particle_dual_sequence',False):return None
    if str(material.get('sfm_particle_shader','')).casefold()!='spritecard':
        raise ValueError('Dual-sequence geometry requires a SpriteCard material')
    if function!='render_animated_sprites':
        raise ValueError('Dual-sequence textures require the verified animated-sprite renderer')
    if renderer.get('animation_fit_lifetime',False) or renderer.get('use animation rate as FPS',False):
        raise ValueError('Dual-sequence fit-lifetime/FPS clock conversion remains unverified')
    from particle_sheet import animation_rate
    primary=animation_rate(renderer);secondary=float(renderer.get('second sequence animation rate',0))
    if not math.isfinite(secondary) or secondary<0:raise ValueError('Invalid secondary particle animation rate')
    mode=material.get('sfm_particle_sequence_blend_mode',0)
    if mode not in (0,1,2):raise ValueError('Unsupported dual-sequence blend mode')
    if material.get('sfm_particle_maxlum_frame_blend1',0):
        raise ValueError('Dual-sequence max-luminance frame blending remains unsupported')
    from particle_dual_sequence_uv import scale_parameters
    scale_parameters(material.get('sfm_particle_sequence_zoom',1.))
    return {'primary_rate':primary,'secondary_rate':secondary,
            'zoom':float(material.get('sfm_particle_sequence_zoom',1.)),
            'blend_mode':int(mode),'blend_primary_frames':bool(material.get('sfm_particle_blend_frames',True))}


def sample(config,sheet,state,age,tables):
    values=[]
    for label,field,rate in (('primary','sequence','primary_rate'),('secondary','secondary_sequence','secondary_rate')):
        key=str(int(state[field]))
        if key not in sheet:raise ValueError('Dual-sequence '+label+' texture has no sequence '+key)
        if key not in tables:tables[key]=Table(sheet[key])
        values.append(tables[key].sample(age,config[rate]))
    return coordinates(*values,config['zoom']),tuple(value.blend for value in values)
