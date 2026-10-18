import unittest
from project_pack import explicit_reference

class PackReferenceTests(unittest.TestCase):
    def test_old_particle_installation_path_is_in_missing_asset_audit(self):
        self.assertEqual(explicit_reference('particleFiles',r'D:\OldSFM\game\workshop\particles\fire.pcf'),'particles/fire.pcf')
    def test_material_and_map_reference_conventions_are_preserved(self):
        self.assertEqual(explicit_reference('mtlName','models/body'),'materials/models/body.vmt')
        self.assertEqual(explicit_reference('mapname','stage'),'maps/stage.bsp')
    def test_unrelated_values_are_ignored(self):
        self.assertIsNone(explicit_reference('name','camera1'))
        self.assertIsNone(explicit_reference('count',5))
