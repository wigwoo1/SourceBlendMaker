"""Experimental pull preflight using statically matched IFM/PET defaults.

Parsing settings does not establish Source force-equation equivalence.
"""
import math
from particle_pull_integrator import vec

def settings(parameters):
    def number(key,default):
        value=float(parameters.get(key,default))
        if not math.isfinite(value):raise ValueError('Nonfinite pull '+key)
        return value
    cp=number('control point number',0)
    if cp!=int(cp) or not 0<=cp<64:raise ValueError('Invalid pull control point')
    local=parameters.get('scale in local space',False)
    if not isinstance(local,(bool,int)) or local not in (False,True):raise ValueError('Invalid pull local-space flag')
    scaling_cp=number('scale force by control point',-1)
    if scaling_cp!=int(scaling_cp) or not -1<=scaling_cp<64:raise ValueError('Invalid pull scaling control point')
    field=number('scale control point field',0)
    if field!=int(field) or not 0<=field<=2:raise ValueError('Invalid pull scaling field')
    unsupported=[]
    # These shared operator fields affect strength and collection time. Until
    # their evaluation is implemented, do not silently treat them as defaults.
    common_defaults = {
        'operator start fadein': 0, 'operator end fadein': 0,
        'operator start fadeout': 0, 'operator end fadeout': 0,
        'operator fade oscillate': 0, 'operator time offset seed': 0,
        'operator time offset min': 0, 'operator time offset max': 0,
        'operator time scale seed': 0, 'operator time scale min': 1,
        'operator time scale max': 1, 'operator time strength random scale max': 1,
        'operator strength scale seed': 0, 'operator strength random scale min': 1,
        'operator strength random scale max': 1,
        'operator strength scale control point': -1, 'operator end cap state': -1,
    }
    for key, default in common_defaults.items():
        if number(key, default) != default:
            unsupported.append('Nondefault shared pull setting: '+key)
    if local:unsupported.append('Local-space component scaling')
    if scaling_cp>=0:unsupported.append('Force magnitude scaled by control point')
    return {'control_point':int(cp),'amount':number('amount of force',0),'power':number('falloff power',2),
            'component_scale':vec(parameters.get('component scale',(1,1,1))),
            'local_space':bool(local),'scale_control_point':int(scaling_cp),'scale_field':int(field),
            'prototype_unsupported_features':unsupported,
            'default_evidence':'Installed IFM/PET statically matched unpack tables; force equations unverified'}
