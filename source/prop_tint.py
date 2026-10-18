"""Isolated static prop diffuse tint; mesh geometry remains shared."""
import bpy

def apply(obj,color):
    rgb=tuple(float(v) for v in color[:3])
    if all(abs(v-1)<1e-6 for v in rgb):return []
    source=obj.instance_collection
    collection=None
    if source is not None:
        collection=bpy.data.collections.new(source.name+' tinted')
        members={old:old.copy() for old in source.all_objects}
        for old,new in members.items():
            collection.objects.link(new)
            if old.parent in members:new.parent=members[old.parent]
        meshes=list(members.values())
    else:meshes=[obj,*obj.children_recursive]
    if not any(mesh.type=='MESH' for mesh in meshes):return ['No imported mesh for prop tint']
    materials={};unsupported=[]
    for mesh in meshes:
        if mesh.type!='MESH':continue
        for slot in mesh.material_slots:
            original=slot.material
            if original is None:continue
            if original not in materials:
                material=original.copy();material.name=original.name+' prop tint'
                nodes=material.node_tree.nodes if material.node_tree else []
                principled=[node for node in nodes if node.type=='BSDF_PRINCIPLED']
                if not principled:unsupported.append(original.name)
                for node in principled:
                    socket=node.inputs['Base Color']
                    if socket.is_linked:
                        source_color=socket.links[0].from_socket
                        multiply=material.node_tree.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
                        multiply.inputs[2].default_value=(*rgb,1)
                        material.node_tree.links.new(source_color,multiply.inputs[1]);material.node_tree.links.new(multiply.outputs[0],socket)
                    else:socket.default_value=tuple(a*b for a,b in zip(socket.default_value,(*rgb,1)))
                material['sfm_prop_tint']=rgb;materials[original]=material
            slot.link='OBJECT';slot.material=materials[original]
    if collection is not None:obj.instance_collection=collection
    obj.color=(*rgb,1);obj['sfm_prop_tint']=rgb
    return unsupported
