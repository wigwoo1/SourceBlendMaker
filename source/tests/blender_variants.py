"""Run using Blender --background --python, then again with --verify after loading."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import bpy

app=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(app))

if '--verify' not in sys.argv:
    from blender_worker import model_variants
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    red=bpy.data.materials.new('Variant Red');blue=bpy.data.materials.new('Variant Blue')
    bpy.ops.mesh.primitive_cube_add();mesh=bpy.context.object;mesh.name='Variant Mesh'
    mesh.data.materials.append(red)
    mesh['skin_groups']={'0':[red.name],'1':[blue.name]}
    mesh.shape_key_add(name='Basis');key=mesh.shape_key_add(name='Face')
    key.data[0].co.z+=.25
    container=NS(objects=[mesh],bodygroups={'body':[mesh]})
    mdl=NS(body_parts=[NS(name='body',models=[NS(vertex_count=0),NS(vertex_count=8)])])
    class Shot:
        def value(self,element,key,t,default):
            return {'skin':0 if t==0 else 1,'body':1 if t<2 else 0,'visible':True}.get(key,default)
    model_variants(container,mdl,{},Shot(),[1,2,3],[0,1,2])
    bpy.context.scene.frame_end=3
    bpy.ops.wm.save_as_mainfile(filepath=str(Path('work/variants.blend').resolve()))

meshes=[o for o in bpy.data.objects if o.type=='MESH']
assert len(meshes)==2
assert meshes[0].data==meshes[1].data
assert meshes[0].data.shape_keys==meshes[1].data.shape_keys
states=[]
for frame,expected in [(1,'Variant Red'),(2,'Variant Blue'),(3,None)]:
    bpy.context.scene.frame_set(frame)
    visible=[o for o in meshes if not o.hide_render]
    assert len(visible)==(1 if expected else 0),(frame,[o.name for o in visible])
    if expected:assert visible[0].material_slots[0].material.name==expected
    states.append({'frame':frame,'visible_material':expected})
if '--verify' in sys.argv:
    Path('outputs/variant_validation.json').write_text(json.dumps({'reopened_without_addons':True,'shared_geometry_and_flex':True,'states':states},indent=2),encoding='utf-8')
print('VARIANTS_VERIFIED',states)
