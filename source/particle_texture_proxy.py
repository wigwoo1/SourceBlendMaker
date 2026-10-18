"""Limited AnimatedTexture parsing; unknown proxies remain explicitly unsupported."""
import math

def animations(proxies):
    supported=[];unsupported=[]
    for name,block in (proxies.items() if proxies else ()):
        if str(name).lower()!='animatedtexture':
            unsupported.append(str(name));continue
        if not hasattr(block,'items'):
            unsupported.append(str(name));continue
        values={str(k).lower():v for k,v in block.items()}
        target=str(values.get('animatedtexturevar','')).lower()
        frame=str(values.get('animatedtextureframenumvar','')).lower()
        expected={'$normalmap':'$bumpframe','$refracttinttexture':'$refracttinttextureframe'}
        try:
            rate=float(values.get('animatedtextureframerate',15));nowrap=int(values.get('animationnowrap',0))
        except (ValueError,TypeError):
            unsupported.append(str(name));continue
        if target not in expected or frame!=expected[target] or nowrap or not math.isfinite(rate) or rate<=0 or any(t==target for t,r in supported):
            unsupported.append(str(name));continue
        supported.append((target,rate))
    return supported,unsupported
