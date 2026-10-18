def switch_images(tree, node, images, choices, frames, curves, factor_callback=None):
    """Bake discrete image choices into native color and alpha node selectors."""
    destinations={name:[link.to_socket for link in node.outputs[name].links]
                  for name in ('Color','Alpha')}
    variants=[node]
    for image in images[1:]:
        variant=tree.nodes.new('ShaderNodeTexImage')
        variant.image=image
        for attr in ('interpolation','projection','projection_blend','extension'):
            setattr(variant,attr,getattr(node,attr))
        variant.inputs['Vector'].default_value=node.inputs['Vector'].default_value
        if node.inputs['Vector'].is_linked:
            tree.links.new(node.inputs['Vector'].links[0].from_socket,variant.inputs['Vector'])
        variants.append(variant)
    for name in destinations:
        output=node.outputs[name]
        for index,variant in enumerate(variants[1:],1):
            mix=tree.nodes.new('ShaderNodeMixRGB')
            mix.blend_type='MIX'
            tree.links.new(output,mix.inputs[1])
            tree.links.new(variant.outputs[name],mix.inputs[2])
            if factor_callback is not None:factor_callback(mix.inputs[0],index)
            else:
                values=[float(choice==index) for choice in choices]
                mix.inputs[0].default_value=values[0]
                curves.add(mix.inputs[0].path_from_id('default_value'),frames,values,'CONSTANT')
            output=mix.outputs[0]
        for destination in destinations[name]:tree.links.new(output,destination)
