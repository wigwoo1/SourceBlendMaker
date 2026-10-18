"""Native per-instance static-prop lighting from this map's VHV files."""
import bpy
from vhv import from_map,model_colors,linear_colors
from bsp_lightmaps import bind_material

ATTRIBUTE='SFM Prop Lighting'


def apply(bsp,objects,hdr=True):
    record={'converted_props':0,'vertices':0,'missing_props':0,'rejected':[],
            'unsupported_materials':[],'render_equivalence_verified':False}
    materials={}
    for obj in objects:
        index=obj.get('sfm_bsp_prop_index')
        source=obj.instance_collection
        if index is None or source is None:continue
        try:
            filename,lighting=from_map(bsp,index,hdr)
            if lighting is None:
                record['missing_props']+=1;continue
            meshes=[mesh for mesh in source.all_objects if mesh.type=='MESH']
            if not meshes:raise ValueError('No imported mesh for baked prop lighting')
            # Validate every group before mutating the prop's collection.
            colors={mesh:linear_colors(model_colors(lighting,mesh)) for mesh in meshes}
            collection=bpy.data.collections.new(source.name+' baked lighting')
            members={old:old.copy() for old in source.all_objects}
            for old,new in members.items():
                collection.objects.link(new)
                if old.parent in members:new.parent=members[old.parent]
                if old not in colors:continue
                new.data=old.data.copy()
                attribute=new.data.color_attributes.get(ATTRIBUTE)
                if attribute:new.data.color_attributes.remove(attribute)
                attribute=new.data.color_attributes.new(name=ATTRIBUTE,type='FLOAT_COLOR',domain='POINT')
                attribute.data.foreach_set('color',colors[old].ravel())
                for slot in new.material_slots:
                    original=slot.material
                    if original is None:continue
                    if original not in materials:
                        material=original.copy();material.name=original.name+' baked prop lighting'
                        if bind_material(material,None,vertex_attribute=ATTRIBUTE):materials[original]=material
                        else:
                            record['unsupported_materials'].append(original.name)
                            bpy.data.materials.remove(material);materials[original]=original
                    slot.link='OBJECT';slot.material=materials[original]
                record['vertices']+=len(colors[old])
            obj.instance_collection=collection
            obj['sfm_prop_lighting_file']=filename
            record['converted_props']+=1
        except Exception as exc:
            record['rejected'].append({'prop':int(index),'object':obj.name,'reason':str(exc)})
    record['unsupported_materials']=sorted(set(record['unsupported_materials']))
    return record
