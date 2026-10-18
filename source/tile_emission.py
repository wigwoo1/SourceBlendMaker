"""User-requested automatic glow, scoped to the terrain-plane tile surface."""
TILE='models/tools/terrain_plane/skin0_vertexlitgeneric'

def is_tile(path):
    return str(path).replace('\\','/').casefold().removeprefix('materials/').removesuffix('.vmt')==TILE

def apply(materials,strength=1.):
    count=0
    for material in materials:
        if not is_tile(material.get('full_path',material.get('sfm_material_source_name',''))) or not material.node_tree:continue
        tree=material.node_tree
        for shader in tree.nodes:
            if shader.type!='BSDF_PRINCIPLED':continue
            base=shader.inputs['Base Color'];emission=shader.inputs['Emission Color']
            for link in list(emission.links):tree.links.remove(link)
            if base.is_linked:tree.links.new(base.links[0].from_socket,emission)
            else:emission.default_value=base.default_value
            power=shader.inputs['Emission Strength']
            for link in list(power.links):tree.links.remove(link)
            power.default_value=strength
            for name,value in (('Alpha',1.),('Transmission Weight',0.)):
                socket=shader.inputs[name]
                for link in list(socket.links):tree.links.remove(link)
                socket.default_value=value
            material['sfm_animated_tile_emission']=True
            count+=1
    return count
