"""Native material fog for separately rendered Source sky geometry."""
import json
import bpy
from mathutils import Vector

def linear_color(text):
    rgb=[float(v)/255 for v in text.split()[:3]]
    return [c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb]+[1.]

def material_fog(original,camera,scale,scene):
    if original.get('full_path','').lower().startswith('tools/'):return original
    material=original.copy();material.name=original.name+' sky fog'
    tree=material.node_tree
    output=next((n for n in tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
    if output is None or not output.inputs['Surface'].is_linked:return original
    source=output.inputs['Surface'].links[0].from_socket
    camera_data=tree.nodes.new('ShaderNodeCameraData')
    fade=tree.nodes.new('ShaderNodeMapRange');fade.clamp=True
    fade.inputs['From Min'].default_value=float(camera.get('fogstart',0))*scale
    fade.inputs['From Max'].default_value=max(float(camera.get('fogend',10000))*scale,fade.inputs['From Min'].default_value+1e-6)
    fade.inputs['To Max'].default_value=max(0,min(1,float(camera.get('fogmaxdensity',1))))
    radial=str(camera.get('fog_radial',camera.get('fogradial','0')))=='1'
    tree.links.new(camera_data.outputs['View Distance' if radial else 'View Z Depth'],fade.inputs['Value'])
    emission=tree.nodes.new('ShaderNodeEmission');emission.name='SFM sky fog color'
    emission.inputs['Color'].default_value=linear_color(camera.get('fogcolor','255 255 255'))
    fog_surface=emission.outputs[0]
    surface=source.node
    if surface.type=='BSDF_PRINCIPLED':
        alpha=surface.inputs['Alpha']
        if alpha.is_linked or alpha.default_value<1:
            transparent=tree.nodes.new('ShaderNodeBsdfTransparent')
            opacity=tree.nodes.new('ShaderNodeMixShader')
            tree.links.new(transparent.outputs[0],opacity.inputs[1]);tree.links.new(fog_surface,opacity.inputs[2])
            if alpha.is_linked:tree.links.new(alpha.links[0].from_socket,opacity.inputs[0])
            else:opacity.inputs[0].default_value=alpha.default_value
            fog_surface=opacity.outputs[0]
    mix=tree.nodes.new('ShaderNodeMixShader')
    tree.links.new(fade.outputs['Result'],mix.inputs[0]);tree.links.new(source,mix.inputs[1])
    tree.links.new(fog_surface,mix.inputs[2]);tree.links.new(mix.outputs[0],output.inputs['Surface'])
    material['sfm_sky_fog']=json.dumps(dict(camera));material['sfm_sky_fog_scene']=scene.name
    return material

def apply(objects,camera,scale,scene):
    if str(camera.get('fogenable','0'))!='1':return []
    copies={};materials={};meshes=[]
    for obj in objects:
        if obj.instance_collection:
            source=obj.instance_collection
            if source not in copies:
                collection=bpy.data.collections.new(source.name+' sky fog')
                members={old:old.copy() for old in source.all_objects}
                for old,new in members.items():
                    collection.objects.link(new)
                    if old.parent in members:new.parent=members[old.parent]
                copies[source]=collection
            obj.instance_collection=copies[source];meshes.extend(obj.instance_collection.all_objects)
        elif obj.type=='MESH':meshes.append(obj)
    for obj in set(meshes):
        if obj.type!='MESH':continue
        for slot in obj.material_slots:
            original=slot.material
            if original is None:continue
            if original not in materials:materials[original]=material_fog(original,camera,scale,scene)
            slot.link='OBJECT';slot.material=materials[original]
    return [m.name for m in materials.values() if m.get('sfm_sky_fog')]

def animate(scene,frames,Curves):
    if not scene.camera:return
    targets=[(material,json.loads(material['sfm_sky_fog'])) for material in bpy.data.materials if material.get('sfm_sky_fog_scene')==scene.name]
    targets=[(material,config) for material,config in targets if str(config.get('fogblend','0'))=='1']
    if not targets:return
    forwards=[]
    for frame in frames:
        scene.frame_set(int(frame));camera=scene.camera.evaluated_get(bpy.context.evaluated_depsgraph_get())
        forwards.append((camera.matrix_world.to_quaternion()@Vector((0,0,-1))).normalized())
    for material,config in targets:
        direction=Vector(tuple(float(v) for v in config.get('fogdir','1 0 0').split())).normalized()
        first=linear_color(config.get('fogcolor','255 255 255'));second=linear_color(config.get('fogcolor2','255 255 255'))
        values=[]
        for forward in forwards:
            weight=max(0,min(1,.5*forward.dot(direction)+.5))
            values.append([a*weight+b*(1-weight) for a,b in zip(first,second)])
        socket=material.node_tree.nodes['SFM sky fog color'].inputs['Color']
        Curves(material.node_tree,material.name+' color',reuse=True).add(socket.path_from_id('default_value'),frames,values)
