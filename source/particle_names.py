"""Resolve capitalization of supported PCF function names; no guessed aliases."""
FUNCTIONS=(
    'render_animated_sprites','render_sprite_trail','render_rope',
    'emit_continuously','emit_instantaneously','emit to maintain count',
    'Radius Random','Lifetime Random','lifetime from sequence',
    'Position From Control Points','Position Along Path Sequential',
    'Rotation Random','Rotation Yaw Random','Rotation Speed Random','Rotation Yaw Flip Random',
    'Position Within Sphere Random','Position Within Box Random',
    'Position Modify Offset Random','Color Random','Alpha Random',
    'Sequence Random','Sequence Two Random','Trail Length Random','Velocity Noise','Velocity Random',
    'Ramp Scalar Linear Random','Remap Initial Scalar','Remap Noise to Scalar','Remap Scalar','Radius Scale','Alpha Fade In Random',
    'Alpha Fade Out Random','Alpha Fade In Simple','Alpha Fade Out Simple',
    'Alpha Fade and Decay','Movement Basic','Movement Lock to Control Point',
    'Lifespan Decay','Color Fade','Rotation Basic','Rotation Spin Roll',
    'Set Control Point Positions',
    'Oscillate Scalar Simple','random force',
    'Force based on distance from plane','Position Along Epitrochoid',
)
NAMES={name.casefold():name for name in FUNCTIONS}

def canonical(name):
    return NAMES.get(name.casefold(),name)

def normalize(definition):
    groups={}
    for group,modules in definition['modules'].items():
        groups[group]=[]
        for module in modules:
            name=canonical(module['function'])
            if name!=module['function']:
                module={**module,'function':name,'source_function':module.get('source_function',module['function'])}
            groups[group].append(module)
    return {**definition,'modules':groups}
