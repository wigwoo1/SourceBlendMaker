"""Recognize neutral controls on the known terrain-plane material template.

Non-neutral/animated controls remain unsupported rather than being discarded.
This is scoped to the template whose proxy layout has been inspected.
"""
import math
import re
from tile_emission import is_tile


def neutral(path, vmt, controls, shot, seconds):
    if not is_tile(path) or str(vmt.shader).lower() != 'vertexlitgeneric' or not seconds:
        return set()
    inputs = {}
    for control in controls:
        for key in control:
            if key.startswith('$'): inputs[key.lower()] = (control, key)
    def constant(key, expected):
        if key not in inputs: return False
        control, original = inputs[key]
        try:
            sample_times=seconds
            if hasattr(shot,'is_constant') and shot.is_constant(control,original):sample_times=seconds[:1]
            return all(math.isfinite(float(value)) and float(value) == expected
                       for value in (shot.value(control, original, t, control[original]) for t in sample_times))
        except (TypeError, ValueError): return False
    def identity(key):
        raw = vmt.get_string(key, '')
        try: values = [float(n) for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', raw)]
        except (TypeError, ValueError): return False
        return values == [1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]
    proxies = vmt.data.get('proxies')
    operations = [(str(kind).lower(),p) for kind,p in proxies.items() if hasattr(p,'get')] if proxies else []
    def writer(target, kind, source):
        matches=[(name,p) for name,p in operations if str(p.get('resultvar','')).lower()==target]
        if len(matches)!=1:return False
        name,p=matches[0]
        if name!=kind or str(p.get('srcvar1','')).lower()!=source:return False
        if kind=='add':return str(p.get('srcvar2','')).lower()=='$zero' and vmt.get_float('$zero',float('nan'))==0
        if kind=='clamp':return float(p.get('min',0))==0 and float(p.get('max',0))>=0
        return False
    result = set()
    # Only claim identity transforms when both the imported matrix and the
    # evaluated authored proxy inputs are identity at all conversion samples.
    for prefix, matrix in (('$basetexture', '$basetexturetransform'), ('$detail', '$detailtexturetransform')):
        expected = {prefix+'_scale_xy': 1., prefix+'_rotate': 0.,
                    prefix+'_translate_x': 0., prefix+'_translate_y': 0.}
        transform = any(kind == 'texturetransform' and
                        str(p.get('resultvar','')).lower() == matrix and
                        str(p.get('scalevar','')).lower() == prefix+'_scale' and
                        str(p.get('rotatevar','')).lower() == prefix+'_rotate' and
                        str(p.get('translatevar','')).lower() == prefix+'_translate'
                        for kind,p in operations)
        bindings=all(writer(prefix+f'_scale[{i}]','add',prefix+'_scale_xy') for i in (0,1)) and all(
            writer(prefix+f'_translate[{i}]','clamp',prefix+'_translate_'+axis) for i,axis in enumerate(('x','y')))
        if transform and bindings and identity(matrix) and all(constant(key, value) for key,value in expected.items()):
            result.update(expected)
    if float(vmt.get_float('$detailblendfactor', 1)) == 0 and constant('$detailblendfactor', 0):
        result.add('$detailblendfactor')
    colors = ('$envmap_color_red', '$envmap_color_green', '$envmap_color_blue')
    tint, _ = vmt.get_vector('$envmaptint', [1,1,1])
    if (len(tint) == 3 and all(float(x) == 0 for x in tint) and all(constant(key,0) for key in colors)
            and all(writer(f'$envmaptint[{i}]','clamp',key) for i,key in enumerate(colors))):
        result.update(colors)
        if '$envmap' in inputs: result.add('$envmap')
    return result
