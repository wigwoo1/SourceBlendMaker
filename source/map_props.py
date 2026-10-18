"""Resolve SourceIO BSP prop placeholders using the job's mounted assets."""
from types import SimpleNamespace
import bpy

def load(assets,objects,warn):
    from SourceIO.blender_bindings.operators.shared_operators import SourceIO_OT_LoadEntity
    from SourceIO.blender_bindings.utils.bpy_utils import find_layer_collection
    class Loader:
        apply_prop_pose=SourceIO_OT_LoadEntity.apply_prop_pose
        def report(self,levels,message):warn(message)
    loader=Loader()
    context=SimpleNamespace(scene=SimpleNamespace(use_instances=True,import_materials=True,
                            replace_entity=False,use_bvlg=False,import_physics=False))
    records=[]
    for obj in objects:
        data=obj.get('entity_data')
        if not data or data.get('imported'):continue
        path=data.get('prop_path')
        if not path or not str(path).lower().endswith('.mdl'):continue
        record={'object':obj.name,'path':str(path),'converted':False}
        tint=data.get('entity',{}).get('tint')
        try:
            SourceIO_OT_LoadEntity.load_mdl(loader,assets.cm,context,obj)
            record['converted']=bool(obj.get('entity_data',{}).get('imported'))
            if record['converted'] and tint:
                from prop_tint import apply
                color=[float(v) for v in str(tint).split()]
                unsupported=apply(obj,color)
                record['tint']=color
                record['tint_converted']=not unsupported
                record['tint_unsupported']=unsupported
                if unsupported:warn(f'Map prop {path}: tint shader unsupported for '+', '.join(unsupported))
            if obj.instance_collection:
                record['instance_collection']=obj.instance_collection.name
                record['mesh_objects']=sum(o.type=='MESH' for o in obj.instance_collection.all_objects)
            else:record['mesh_objects']=sum(o.type=='MESH' for o in obj.children_recursive)
            if not record['converted']:warn(f'Map prop not resolved: {path}')
        except Exception as exc:
            record['error']=str(exc);warn(f'Map prop {path}: {exc}')
        records.append(record)
    bpy.context.view_layer.update()
    template=bpy.data.collections.get('MASTER_INSTANCES_DO_NOT_EDIT')
    if template:
        layer=find_layer_collection(bpy.context.view_layer.layer_collection,template.name)
        if layer:layer.exclude=True
    return records
