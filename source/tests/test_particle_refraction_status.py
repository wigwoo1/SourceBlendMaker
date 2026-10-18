import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_refraction_status import failed
class RefractionStatusTests(unittest.TestCase):
    def test_failure_preserves_geometry_and_other_effects(self):
        descriptor={'rendered':True,'bake':[{'material_path':'particles/warp.vmt','rendered':True,'geometry_generated':True},{'material_path':'particles/fire.vmt','rendered':True}]}
        self.assertEqual(failed(descriptor,['materials/particles/warp.vmt'],'No compositor'),1)
        self.assertFalse(descriptor['rendered']);self.assertTrue(descriptor['bake'][0]['geometry_generated']);self.assertFalse(descriptor['bake'][0]['rendered']);self.assertTrue(descriptor['bake'][1]['rendered'])
    def test_unrelated_failure_does_not_change_success(self):
        descriptor={'bake':[{'material_path':'fire.vmt','rendered':True}]}
        self.assertEqual(failed(descriptor,['warp.vmt'],'failed'),0);self.assertTrue(descriptor['rendered'])
