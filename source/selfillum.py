"""Native Principled self-illumination overrides; never enabled implicitly."""
def color_value(value):
    """Decode typed DMX colors and Source vector strings without guessing units."""
    import math
    integer=type(value).__name__=='Color'
    if isinstance(value,str):
        raw=value.strip();integer=raw.startswith('{')
        components=raw.strip('[]{}').replace(',',' ').split()
    elif isinstance(value,(int,float)):components=[value]*3
    else:components=list(value)
    if len(components)<3:raise ValueError('Material color requires three components')
    rgb=[float(v)/(255. if integer else 1.) for v in components[:3]]
    if not all(math.isfinite(v) for v in rgb):raise ValueError('Material color must be finite')
    return rgb+[1.]

def sync_color(material, shader):
    tint=material.node_tree.nodes.get('Source selfillum tint')
    if tint is None:return
    base=shader.inputs['Base Color']
    if base.is_linked:material.node_tree.links.new(base.links[0].from_socket,tint.inputs[1])
    else:tint.inputs[1].default_value=base.default_value

def ensure_selfillum(material, shader):
    tree=material.node_tree
    tint=tree.nodes.get('Source selfillum tint')
    if tint is None:
        tint=tree.nodes.new('ShaderNodeMixRGB');tint.name='Source selfillum tint'
        tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1.;tint.inputs[2].default_value=(1,1,1,1)
        tree.links.new(tint.outputs[0],shader.inputs['Emission Color'])
    sync_color(material,shader)
    strength=tree.nodes.get('Source selfillum enabled')
    if strength is None:
        strength=tree.nodes.new('ShaderNodeMath');strength.name='Source selfillum enabled';strength.operation='MULTIPLY'
        socket=shader.inputs['Emission Strength']
        strength.inputs[0].default_value=socket.default_value if material.get('source_selfillum') else 1.
        if socket.is_linked:tree.links.new(socket.links[0].from_socket,strength.inputs[0])
        elif not material.get('source_selfillum'):
            texture=tree.nodes.get('$basetexture')
            if texture:tree.links.new(texture.outputs['Alpha'],strength.inputs[0])
        strength.inputs[1].default_value=float(bool(material.get('source_selfillum')))
        tree.links.new(strength.outputs[0],socket)

def override_socket(material, shader, key):
    if shader is None:return None
    ensure_selfillum(material,shader)
    name='Source selfillum enabled' if key.lower()=='$selfillum' else 'Source selfillum tint'
    node=material.node_tree.nodes.get(name)
    return node.inputs[1 if key.lower()=='$selfillum' else 2]
