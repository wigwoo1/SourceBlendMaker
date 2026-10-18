"""Save/reopen and render a real animated scattering beam without addons."""
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

if '--verify' not in sys.argv:
    import blender_worker as worker
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    class Element(dict):name='Test spotlight'
    class Shot:
        def value(self,e,key,t,default):
            return {'volumetric':t<2,'volumetricIntensity':1 if t<1 else 2,'maxDistance':200,'horizontalFOV':35,'verticalFOV':35}.get(key,default)
    data=bpy.data.lights.new('Test spotlight','SPOT');data.energy=2000;data.spot_size=.61
    light=bpy.data.objects.new('Test spotlight',data);bpy.context.scene.collection.objects.link(light)
    worker.import_volumetric(Shot(),Element(),light,[1,2,3],[0,1,2])
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.render.resolution_x=256;scene.render.resolution_y=256;scene.render.resolution_percentage=100
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0
    camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera)
    camera.location=(7,-9,-2.5)
    from mathutils import Vector
    camera.rotation_euler=(Vector((0,0,-2.5))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=6;scene.camera=camera
    bpy.ops.wm.save_as_mainfile(filepath=str(Path('work/volumetric.blend').resolve()))
else:
    scene=bpy.context.scene;beam=bpy.data.objects['Test spotlight volumetric beam']
    scatter=next(n for n in beam.data.materials[0].node_tree.nodes if n.type=='VOLUME_SCATTER')
    values=[];brightness=[]
    for frame in (1,2,3):
        scene.frame_set(frame);values.append(scatter.inputs['Density'].default_value)
        scene.render.filepath=str(Path(f'outputs/volumetric-test-{frame}.png').resolve())
        bpy.ops.render.render(write_still=True)
        image=bpy.data.images.load(scene.render.filepath,check_existing=False)
        pixels=list(image.pixels);brightness.append(sum(pixels[i] for i in range(len(pixels)) if i%4!=3)/(256*256*3))
        bpy.data.images.remove(image)
    assert abs(values[1]/values[0]-2)<.001 and values[2]==0,values
    assert brightness[0]>.0001 and brightness[2]<brightness[0]*.01,brightness
    Path('outputs/volumetric_validation.json').write_text(json.dumps({'density':values,'render_mean':brightness,'saved_native_animation':True,'autoexec_disabled':True},indent=2))
    print('VOLUMETRIC TEST PASSED',values,brightness)
