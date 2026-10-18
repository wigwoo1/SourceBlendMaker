import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
    import bpy
except ImportError:bpy=None


@unittest.skipIf(bpy is None,"Run using Blender's Python")
class DualBlendMaterialTests(unittest.TestCase):
    def test_all_blend_modes_render_color_and_opacity_separately(self):
        from particle_dual_sequence_blend import create_group,combine
        bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene
        scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=16;scene.render.resolution_y=16
        scene.render.resolution_percentage=100;scene.render.image_settings.file_format='OPEN_EXR'
        scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='32'
        scene.render.film_transparent=True;scene.view_settings.view_transform='Standard'
        camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera)
        camera.location=(0,0,2);camera.data.type='ORTHO';camera.data.ortho_scale=1;scene.camera=camera
        bpy.ops.mesh.primitive_plane_add(size=2);plane=bpy.context.object
        primary=(.2,.4,.6,.2);secondary=(.8,.1,.3,.7)
        with tempfile.TemporaryDirectory() as directory:
            for mode in (0,1,2):
                material=bpy.data.materials.new('blend '+str(mode));material.use_nodes=True
                tree=material.node_tree;tree.nodes.clear()
                group=tree.nodes.new('ShaderNodeGroup');group.node_tree=create_group(mode)
                group.inputs['Primary Color'].default_value=(*primary[:3],1)
                group.inputs['Secondary Color'].default_value=(*secondary[:3],1)
                group.inputs['Primary Alpha'].default_value=primary[3];group.inputs['Secondary Alpha'].default_value=secondary[3]
                emission=tree.nodes.new('ShaderNodeEmission');output=tree.nodes.new('ShaderNodeOutputMaterial')
                tree.links.new(emission.outputs[0],output.inputs[0])
                plane.data.materials.clear();plane.data.materials.append(material)
                bpy.ops.wm.save_as_mainfile(filepath=str(Path(directory)/f'mode_{mode}.blend'))
                bpy.ops.wm.open_mainfile(filepath=str(Path(directory)/f'mode_{mode}.blend'))
                scene=bpy.context.scene;plane=bpy.data.objects['Plane'];tree=plane.active_material.node_tree
                group=next(n for n in tree.nodes if n.type=='GROUP')
                emission=next(n for n in tree.nodes if n.type=='EMISSION')
                self.assertEqual(group.node_tree['sfm_sequence_blend_mode'],mode)
                expected=combine(primary,secondary,mode)
                for channel in ('Color','Alpha'):
                    tree.links.new(group.outputs[channel],emission.inputs['Color'])
                    scene.render.filepath=str(Path(directory)/f'{mode}_{channel}.exr')
                    bpy.ops.render.render(write_still=True)
                    image=bpy.data.images.load(scene.render.filepath,check_existing=False)
                    i=(8*16+8)*4;pixel=tuple(image.pixels[i:i+3]);bpy.data.images.remove(image)
                    reference=expected[:3] if channel=='Color' else (expected[3],)*3
                    # Compare through the same render storage path. EEVEE's
                    # intermediate precision can quantize .45 to .44995117
                    # even when the final EXR requests 32-bit channels.
                    tree.links.remove(emission.inputs['Color'].links[0])
                    emission.inputs['Color'].default_value=(*reference,1)
                    scene.render.filepath=str(Path(directory)/f'{mode}_{channel}_reference.exr')
                    bpy.ops.render.render(write_still=True)
                    image=bpy.data.images.load(scene.render.filepath,check_existing=False)
                    rendered_reference=tuple(image.pixels[i:i+3]);bpy.data.images.remove(image)
                    for a,b in zip(pixel,rendered_reference):
                        self.assertAlmostEqual(a,b,places=5,msg=(mode,channel,pixel,rendered_reference))


if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
