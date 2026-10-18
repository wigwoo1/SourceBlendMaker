import importlib.util
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'vendor/SourceIO/blender_bindings/source1/bsp/entities/light_values.py'
spec=importlib.util.spec_from_file_location('map_light_values',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class MapLightValuesTests(unittest.TestCase):
    def test_explicit_hdr_wins_without_fallback_multiplier(self):
        self.assertEqual(module.select_light_values([255,128,0,200],[40,80,120,600],{'_lightscalehdr':.5}),((40.,80.,120.,600.),1.))

    def test_both_sentinel_brightness_variants_use_ldr(self):
        for brightness in (-1,1):
            with self.subTest(brightness=brightness):
                self.assertEqual(module.select_light_values([255,128,0,200],[-1,-1,-1,brightness],{'_lightscalehdr':.5}),((255.,128.,0.,200.),.5))

    def test_scale_key_case_and_zero_hdr(self):
        self.assertEqual(module.select_light_values([1,2,3,4],[-1,-1,-1,1],{'_lightscaleHDR':2})[1],2)
        self.assertEqual(module.select_light_values([1,2,3,4],[0,0,0,0],{}),((0.,0.,0.,0.),1.))

    def test_invalid_values(self):
        for hdr in ([1,2,3],[1,2,3,float('nan')]):
            with self.assertRaises(ValueError):module.select_light_values([1,2,3,4],hdr,{})

if __name__=='__main__':unittest.main()
