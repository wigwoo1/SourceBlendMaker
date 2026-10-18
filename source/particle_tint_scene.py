"""Resolve optional particle tint through selected asset mounts and shot CPs."""
import math
from particle_tint_provider import SceneTintProvider
from particle_tint_map_query import MapTintQuery

def required(descriptor):
    return any(m.get('function','').casefold()=='color random' and
               m.get('parameters',{}).get('operator enabled',True) and
               float(m.get('parameters',{}).get('tint_perc',0))!=0
               for d in descriptor.get('definitions',[]) for m in d.get('modules',{}).get('initializers',[]))

def prepare(shot,descriptor,scene,assets,fps,*,scale=.0254,settings=None):
    settings={} if settings is None else dict(settings)
    path=str(shot.map or '').replace('\\','/')
    if not path:raise ValueError('Particle tint requires a session map')
    if not path.startswith('maps/'):path='maps/'+path
    if not path.lower().endswith('.bsp'):path+='.bsp'
    if ':' in path or any(p in ('','..') for p in path.split('/')):
        raise ValueError('Invalid particle tint map path')
    buffer=assets.buffer(path)
    if buffer is None:raise ValueError('Missing particle tint map: '+path)
    buffer.seek(0)
    query=MapTintQuery(buffer.read(),hdr=settings.get('hdr',True),baked_ambient=True,
        radius_multiplier=settings.get('radius_multiplier',1000.),
        style_value=settings.get('style_value',264),minimum_brightness=settings.get('minimum_brightness',.0002),
        capacity=settings.get('capacity',3))
    controls={o.get('sfm_transform_id'):o for o in scene.objects if o.get('sfm_transform_id')}
    points=descriptor.get('control_points',[])
    def position(cp,time):
        if cp>=len(points) or points[cp].get('id') not in controls:
            raise ValueError('Particle tint control point unavailable: '+str(cp))
        evaluated=shot.start+(scene.frame_current+scene.frame_subframe-1)/fps
        if not math.isfinite(evaluated) or abs(evaluated-time)>1e-5:
            raise ValueError('Particle tint control sampled at wrong shot time')
        return tuple(controls[points[cp]['id']].matrix_world.translation)
    provider=SceneTintProvider(descriptor['definitions'],position,query,scale=scale,context_position=(0.,0.,0.))
    report=dict(map=path,hdr=settings.get('hdr',True),approximate=True,
        sampling='Particle birth time, not verified Source collection step endpoint',
        lighting='Static BSP ambient/world lights; dynamic styles unsupported',
        initial_context_position_fixture=[0.,0.,0.],source_visual_parity=False)
    return provider,report
