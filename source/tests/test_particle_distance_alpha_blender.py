import sys,tempfile,unittest,json,random
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as f
bpy=f.bpy

@unittest.skipIf(bpy is None,"Run using Blender's Python")
class DistanceAlphaTests(unittest.TestCase):
    def setUp(self):bpy.ops.wm.read_factory_settings(use_empty=True)
    def test_outline_nodes_match_numeric_shader_outputs_after_save_reopen(self):
        from particle_distance_alpha import nodes,shade,ATTRIBUTE,shader_color
        scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE'
        scene.render.resolution_x=scene.render.resolution_y=16;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32'
        camera=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(camera)
        camera.location=(0,0,2);camera.data.type='ORTHO';camera.data.ortho_scale=1;scene.camera=camera
        bpy.ops.mesh.primitive_plane_add(size=2);plane=bpy.context.object
        attr=plane.data.color_attributes.new(name=ATTRIBUTE,type='FLOAT_COLOR',domain='CORNER')
        outline=(*shader_color((.25,.5,.75)),.4)
        for v in attr.data:v.color=outline
        material=bpy.data.materials.new('distance');material.use_nodes=True
        tree=material.node_tree;tree.nodes.clear();plane.data.materials.append(material)
        rgb=tree.nodes.new('ShaderNodeRGB');rgb.outputs[0].default_value=(.2,.4,.6,1)
        alpha=tree.nodes.new('ShaderNodeValue');alpha.name='distance value'
        config=dict(outline=True,color=(1,.5,.25),alpha=.5,bounds=(.415,.44,.49,.5),per_particle=True)
        color_out,alpha_out=nodes(tree,rgb.outputs[0],alpha.outputs[0],config)
        emission=tree.nodes.new('ShaderNodeEmission');emission.name='probe'
        output=tree.nodes.new('ShaderNodeOutputMaterial');tree.links.new(emission.outputs[0],output.inputs[0])
        tree.links.new(color_out,emission.inputs['Color'])
        # Named reroutes preserve explicit socket references over save/reopen.
        for name,socket in (('color probe',color_out),('alpha probe',alpha_out)):
            reroute=tree.nodes.new('NodeReroute');reroute.name=name;tree.links.new(socket,reroute.inputs[0])
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'outline.blend');bpy.ops.wm.save_as_mainfile(filepath=path);bpy.ops.wm.open_mainfile(filepath=path)
            scene=bpy.context.scene;tree=bpy.data.materials['distance'].node_tree;emission=tree.nodes['probe']
            def render(name):
                scene.render.filepath=str(Path(directory)/(name+'.exr'));bpy.ops.render.render(write_still=True)
                image=bpy.data.images.load(scene.render.filepath,check_existing=False);i=(8*16+8)*4
                pixel=tuple(image.pixels[i:i+3]);bpy.data.images.remove(image);return pixel
            for a in (.2,.4275,.47,.495,.5,.75):
                tree.nodes['distance value'].outputs[0].default_value=a
                expected=shade((1,1,1,a),(.2,.4,.6,1),(1,.5,.25,.5),outline,config['bounds'])
                for channel in ('color','alpha'):
                    tree.links.new(tree.nodes[channel+' probe'].outputs[0],emission.inputs['Color'])
                    pixel=render('value')
                    tree.links.remove(emission.inputs['Color'].links[0])
                    target=expected[:3] if channel=='color' else (expected[3],)*3
                    emission.inputs['Color'].default_value=(*target,1)
                    reference=render('reference')
                    for x,y in zip(pixel,reference):self.assertAlmostEqual(x,y,delta=.0003,msg=(a,channel,pixel,reference))
    def test_glow_random_is_separate_from_body_in_both_birth_paths(self):
        from mathutils import Matrix
        from particle_sprite_state import sample as legacy,linear_color
        from particle_ordered_birth import sample as ordered
        d=f.definition('glow',0,None,f.module('emit_instantaneously',num_to_emit=1),[0,0,0])
        d['parameters']['color']=[12,34,56,255]
        d['modules']['initializers'].append(f.module('Color Random',**{'output field':22,'color1':[64,128,192,255],'color2':[64,128,192,255]}))
        a=legacy(d,random.Random(1),1,Matrix.Identity(3))
        b,_=ordered(d,random.Random(1),1,0,0,lambda cp:((0,0,0),Matrix.Identity(3)),(0,0,0))
        for state in (a,b):
            self.assertEqual(tuple(state['rgb']),tuple(linear_color([12,34,56,255])))
            self.assertEqual(state['outline_rgb'],(64/255,128/255,192/255))
    def test_baker_writes_outline_vertex_attribute(self):
        from particle_bake import bake
        from particle_distance_alpha import ATTRIBUTE
        base=f.ChildControlPointBakeTests();base.setUp();base.material['sfm_particle_distance_alpha']='{}'
        d=f.definition('outline',0,None,f.module('emit_instantaneously',num_to_emit=1),[0,0,0])
        d['children']=[]
        records=bake(f.System(),{'definitions':[d],'control_points':[{'id':'cp0'}]},f.Shot(),base.scene,[1,6],[0,.5],10,{'fixture.vmt':base.material},f.Curves,scale=1)
        self.assertTrue(all(not row.get('reason') for row in records),records)
        meshes=[o.data for o in base.scene.objects if o.get('sfm_baked_particle_effect')=='outline']
        self.assertTrue(meshes)
        for mesh in meshes:
            self.assertEqual(len(mesh.color_attributes[ATTRIBUTE].data),len(mesh.loops))
            for value in mesh.color_attributes[ATTRIBUTE].data:self.assertEqual(tuple(value.color),(1,1,1,1))

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
