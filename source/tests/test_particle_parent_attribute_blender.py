"""Native initializer-only fixture; original Blink still needs live operators."""
import math
import sys
import tempfile
import unittest
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import test_particle_child_cp_blender as fixture
from particle_parent_attribute import NAME


@unittest.skipIf(fixture.bpy is None, "Run using Blender's Python")
class ParentAttributeBakeTests(unittest.TestCase):
    def setUp(self):
        fixture.bpy.ops.wm.read_factory_settings(use_empty=True)
        self.base = fixture.ChildControlPointBakeTests()
        self.base.setUp()

    def bake(self, disabled=False, birth_time=.5):
        from particle_bake import bake
        m = fixture.module
        parent = fixture.definition('attribute parent', 0, None, m('emit_instantaneously', num_to_emit=1), [2, 0, 0])
        parent['modules']['initializers'][2] = m('Radius Random', radius_min=4., radius_max=4.)
        parent['modules']['operators'].append(m('Radius Scale', start_time=0., end_time=1., radius_start_scale=1., radius_end_scale=3.))
        child = fixture.definition('attribute child', 1, 0,
                                   m('emit_instantaneously', num_to_emit=1, emission_start_time=birth_time), [0, 0, 0])
        child['modules']['initializers'][0] = m('Position From Parent Particles')
        child['modules']['initializers'][1] = m('Lifetime Random', lifetime_min=.1, lifetime_max=.1)
        child['modules']['initializers'][2] = m('Radius Random', radius_min=100., radius_max=100.)
        child['modules']['initializers'].extend([
            m(NAME, **{'Inherited Field': 1, 'operator enabled': not disabled}),
            m(NAME, **{'Scale': .25, 'operator enabled': not disabled})])
        self.contexts = {}
        class Shot(fixture.Shot):
            duration = 3.
        records = bake(fixture.System(), {'definitions': [parent, child],
                       'control_points': [{'id': 'cp0'}], 'random_seed': 1},
                       Shot(), self.base.scene, [1, 12, 21, 45, 53], [0., .55, 1., 2.2, 2.6], 20.,
                       {'fixture.vmt': self.base.material}, fixture.Curves,
                       scale=1., simulation_contexts=self.contexts)
        self.assertTrue(all(not row.get('reason') for row in records), records)
        return records

    def meshes(self):
        return {obj['sfm_baked_frame']: obj for obj in self.base.scene.objects
                if obj.get('sfm_baked_particle_effect') == 'attribute child'}

    def test_live_parent_radius_and_total_lifetime_survive_save_reopen(self):
        records = self.bake()
        child = records[1]
        self.assertEqual(self.contexts[1].lifetimes, {0: 2.})
        self.assertAlmostEqual(self.contexts[1].births[0].time, .5, places=8)
        self.assertEqual(set(self.meshes()), {12, 21, 45})
        for obj in self.meshes().values():
            self.assertAlmostEqual(math.dist(obj.data.vertices[0].co, obj.data.vertices[1].co), 3., places=5)
        self.assertEqual(child['parent_attribute_birth_samples'][0]['values'],
                         [{'field': 1, 'value': 2.}, {'field': 3, 'value': 1.5}])
        name = self.base.scene.name
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'parent-attribute.blend')
            fixture.bpy.ops.wm.save_as_mainfile(filepath=path)
            fixture.bpy.ops.wm.open_mainfile(filepath=path)
            self.base.scene = fixture.bpy.data.scenes[name]
            self.assertEqual(set(self.meshes()), {12, 21, 45})
            for obj in self.meshes().values():
                self.assertAlmostEqual(math.dist(obj.data.vertices[0].co, obj.data.vertices[1].co), 3., places=5)

    def test_disabled_inheritance_keeps_authored_child_values(self):
        self.bake(disabled=True)
        self.assertEqual(set(self.meshes()), {12})
        obj = self.meshes()[12]
        self.assertAlmostEqual(math.dist(obj.data.vertices[0].co, obj.data.vertices[1].co), 200., places=4)

    def test_expired_parent_does_not_create_child_at_fabricated_origin(self):
        self.bake(birth_time=2.2)
        self.assertEqual(self.meshes(), {})


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)
