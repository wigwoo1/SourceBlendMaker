import sys,unittest,json,random,tempfile
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture
from particle_dual_sequence import settings,sample
from particle_bake import plan


def sheet():
    return {str(i):{'clamp':False,'duration':2.,'frames':[
        {'duration':1.,'coordinates':[(i/10,0,i/10+.2,.2)]},
        {'duration':1.,'coordinates':[(i/10,.2,i/10+.2,.4)]}]} for i in (0,4,7)}


def definition():
    result=fixture.definition('dual fixture',0,None,fixture.module('emit_instantaneously',num_to_emit=1),[0,0,0])
    result['children']=[]
    result['modules']['initializers'].append(fixture.module('Sequence Two Random',sequence_min=4,sequence_max=4))
    result['modules']['renderers'][0]['parameters']['second sequence animation rate']=.25
    return result


MATERIAL={'sfm_particle_shader':'SpriteCard','sfm_particle_dual_sequence':True,
          'sfm_particle_sequence_blend_mode':1,'sfm_particle_sequence_zoom':4.}


class DualIntegrationPlanningTests(unittest.TestCase):
    def test_supported_definition_reaches_material_aware_plan(self):
        config=plan(definition(),sheet(),material=MATERIAL)
        self.assertEqual(config['dual_sequence']['blend_mode'],1)
        self.assertEqual(config['dual_sequence']['secondary_rate'],.25)

    def test_unverified_clocks_and_other_renderers_are_explicit(self):
        for renderer,function in (({'animation_fit_lifetime':True},'render_animated_sprites'),
                                  ({'use animation rate as FPS':True},'render_animated_sprites'),
                                  ({},'render_sprite_trail')):
            with self.assertRaises(ValueError):settings(MATERIAL,renderer,function)
        with self.assertRaisesRegex(ValueError,'max-luminance'):
            settings({**MATERIAL,'sfm_particle_maxlum_frame_blend1':1},{},'render_animated_sprites')

    def test_sampler_keeps_independent_sequences_and_reuses_tables(self):
        config=settings(MATERIAL,{'second sequence animation rate':.25},'render_animated_sprites')
        cache={};state={'sequence':0,'secondary_sequence':4}
        uv,a=sample(config,sheet(),state,0.,cache);first=cache['4']
        later,b=sample(config,sheet(),state,.5,cache)
        self.assertIs(cache['4'],first);self.assertEqual(set(cache),{'0','4'})
        self.assertNotEqual(uv['secondary_current'],later['secondary_current'])
        self.assertNotEqual(a,b)
        with self.assertRaisesRegex(ValueError,'secondary texture has no sequence'):
            sample(config,sheet(),{'sequence':0,'secondary_sequence':5},0.,cache)


@unittest.skipIf(fixture.bpy is None,"Run using Blender's Python")
class DualSequenceBakeTests(unittest.TestCase):
    def setUp(self):
        fixture.bpy.ops.wm.read_factory_settings(use_empty=True)
        self.base=fixture.ChildControlPointBakeTests();self.base.setUp()
        for key,value in MATERIAL.items():self.base.material[key]=value
        self.base.material['sfm_particle_sheet']=json.dumps(sheet())

    def bake(self):
        from particle_bake import bake
        return bake(fixture.System(),{'definitions':[definition()],'control_points':[{'id':'cp0'}],'random_seed':1},
                    fixture.Shot(),self.base.scene,[1,6],[0.,.5],10.,{'fixture.vmt':self.base.material},fixture.Curves,scale=1.)

    def objects(self):
        return sorted((o for o in self.base.scene.objects if o.get('sfm_baked_frame') is not None),key=lambda o:o['sfm_baked_frame'])

    def snapshot(self):
        from particle_dual_sequence_material import UV_NAMES,BLEND_NAMES
        return [({name:[tuple(v.uv) for v in obj.data.uv_layers[name].data] for name in UV_NAMES},
                 {name:[v.value for v in obj.data.attributes[name].data] for name in BLEND_NAMES}) for obj in self.objects()]

    def test_actual_baker_writes_animated_uv_layers_and_frame_attributes(self):
        records=self.bake();self.assertFalse(records[0].get('reason'),records)
        values=self.snapshot();self.assertEqual(len(values),2)
        self.assertNotEqual(values[0],values[1])
        self.assertEqual(records[0]['dual_sequence']['zoom'],4)
        self.assertTrue(all(len(o.data.uv_layers)==5 for o in self.objects()))

    def test_secondary_birth_writes_preserve_primary_in_both_paths(self):
        from mathutils import Matrix
        from particle_sprite_state import sample as legacy
        from particle_ordered_birth import sample as ordered
        d=definition();d['modules']['initializers'].append(fixture.module('Sequence Two Random',sequence_min=7,sequence_max=7))
        states=(legacy(d,random.Random(1),1.,Matrix.Identity(3)),
                ordered(d,random.Random(1),1.,0.,0,lambda cp:((0,0,0),Matrix.Identity(3)),(0,0,0))[0])
        for state in states:self.assertEqual((state['sequence'],state['secondary_sequence']),(0,7))

    def test_saved_bake_preserves_uvs_and_float_attributes(self):
        records=self.bake();self.assertFalse(records[0].get('reason'),records)
        expected=self.snapshot();name=self.base.scene.name
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'dual.blend')
            fixture.bpy.ops.wm.save_as_mainfile(filepath=path);fixture.bpy.ops.wm.open_mainfile(filepath=path)
            self.base.scene=fixture.bpy.data.scenes[name]
            self.assertEqual(self.snapshot(),expected)


if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
