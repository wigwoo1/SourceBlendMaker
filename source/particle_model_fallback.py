"""SFM CDmeParticleSystemQuery fallback when no control model is supplied.

Installed ifm.dll slot 16, 0x102d3f14, copies the CP position. Hitbox
coordinates and indices are zero. Attached-model hitbox sampling is separate.
"""
import copy
import math


def resolve_lerp(definition, descriptor):
    modules=[m for m in definition['modules']['operators']
             if m['function']=='Movement Lerp to Hitbox' and m['parameters'].get('operator enabled',True)]
    if not modules:return definition,False
    if descriptor.get('control_models'):
        raise ValueError('Movement Lerp to Hitbox with attached models requires animated hitbox history')
    for module in modules:
        cp=float(module['parameters'].get('control point number',0))
        if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<len(descriptor.get('control_points',[])):
            raise ValueError('Hitbox movement fallback requires a valid control point')
    # Installed 0x102795d6 tests the refreshed hitbox count. No model makes
    # query slot 19 return zero; the operator exits before any particle write.
    result=copy.deepcopy(definition)
    result['modules']['operators']=[m for m in result['modules']['operators']
        if not (m['function']=='Movement Lerp to Hitbox' and m['parameters'].get('operator enabled',True))]
    return result,True


def resolve(definition, descriptor):
    modules=[m for m in definition['modules']['initializers']
             if m['function']=='Position on Model Random' and m['parameters'].get('operator enabled',True)]
    if not modules:
        return definition,False
    if descriptor.get('control_models'):
        raise ValueError('Position on Model Random with attached models requires animated hitbox sampling')
    if len(modules)!=1:
        raise ValueError('Repeated model position initializers are unverified')
    p=modules[0]['parameters']
    cp=float(p.get('control_point_number',0))
    if not math.isfinite(cp) or cp!=int(cp) or not 0<=cp<len(descriptor.get('control_points',[])):
        raise ValueError('Model position fallback requires a valid control point')
    for key,default in (('operator strength scale control point',-1),('operator end cap state',-1),
                        ('operator time scale seed',0),('operator strength scale seed',0),
                        ('operator time offset seed',0),('operator start fadein',0),
                        ('operator end fadein',0),('operator start fadeout',0),
                        ('operator end fadeout',0),('operator fade oscillate',0)):
        if float(p.get(key,default))!=default:
            raise ValueError('Model position fallback shared timing/strength gate is unverified')
    result=copy.deepcopy(definition)
    for module in result['modules']['initializers']:
        if module['function']=='Position on Model Random' and module['parameters'].get('operator enabled',True):
            module['function']='Position From Control Points'
            module['parameters']={'functionName':'Position From Control Points','Starting Control Point':int(cp)}
    return result,True
