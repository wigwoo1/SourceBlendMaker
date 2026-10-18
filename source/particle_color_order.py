"""Ordered RGB writes: fade uses birth color; CP lighting reads current color.

Offline evaluation uses the sampled particle position for lighting; Source
operator-time positions, shared strength and color-space parity remain limited.
"""
from particle_color_fade import color as fade

def evaluate(modules,initial,fraction,decode,lighting):
    current=tuple(initial)
    for module in modules:
        p=module['parameters']
        if not p.get('operator enabled',True):continue
        if module['function']=='Color Fade':
            if p.get('fade_start_time',0)==p.get('fade_end_time',1):continue
            current=fade(initial,decode(p.get('color_fade',[255]*4)),fraction,p)
        elif module['function']=='Color Light from Control Point':current=tuple(lighting(current))
    return current
