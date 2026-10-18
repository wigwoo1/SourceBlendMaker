"""Select explicit HDR light color or the scaled LDR fallback."""
import math


def select_light_values(ldr, hdr, raw):
    ldr = tuple(float(value) for value in ldr)
    hdr = tuple(float(value) for value in hdr)
    if len(ldr) != 4 or len(hdr) != 4:
        raise ValueError('Map light requires RGB and brightness')
    if not all(math.isfinite(value) for value in ldr + hdr):
        raise ValueError('Map light contains nonfinite values')
    # Generated Source entity classes default to -1 -1 -1 1. The RGB
    # sentinel controls fallback; its brightness component is irrelevant.
    fallback = hdr[:3] == (-1., -1., -1.)
    scale = float(raw.get('_lightscaleHDR', raw.get('_lightscalehdr', 1))) if fallback else 1.
    if not math.isfinite(scale):
        raise ValueError('Map HDR light scale is nonfinite')
    return (ldr if fallback else hdr), scale
