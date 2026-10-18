import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_distance_alpha import shade
class OutlineTests(unittest.TestCase):
    bounds=(.415,.44,.49,.5)
    def sample(self,a,vertex=(1,1,1,1),outline=(1,1,1,.5),particle=(1,1,1,1),bright=1):
        return shade((1,1,1,a),vertex,outline,particle,self.bounds,bright)
    def test_disabled_distance_flag_keeps_regular_material_path(self):
        from particle_distance_alpha import settings
        class VMT:
            def get_int(self,key,default):return 0
        self.assertIsNone(settings(VMT()))
    def test_soft_edges_fail_explicitly(self):
        from particle_distance_alpha import settings
        class VMT:
            def get_int(self,key,default):return 1 if key in ('$distancealpha','$softedges') else default
        with self.assertRaisesRegex(ValueError,'derivative'):settings(VMT())
    def test_dual_distance_combination_is_not_silently_approximated(self):
        from particle_distance_alpha import settings
        class VMT:
            def get_int(self,key,default):return 1 if key in ('$distancealpha','$dualsequence') else default
        with self.assertRaisesRegex(ValueError,'dual'):settings(VMT())
    def test_outline_power_conversion_is_independent_of_alpha(self):
        from particle_distance_alpha import shader_color
        self.assertEqual(shader_color((0,1,.5)),(0,1,.5**2.2))
    def test_distant_background_becomes_fully_transparent(self):
        self.assertEqual(self.sample(.2),(0,0,0,0))
    def test_outer_boundary_is_zero(self):self.assertEqual(self.sample(.415),(0,0,0,0))
    def test_outer_midpoint_is_smooth_half(self):
        for a,b in zip(self.sample(.4275),(.5,.5,.5,.25)):self.assertAlmostEqual(a,b)
    def test_outer_inner_boundary_has_full_outline(self):
        for a,b in zip(self.sample(.44),(1,1,1,.5)):self.assertAlmostEqual(a,b)
    def test_outline_plateau(self):self.assertEqual(self.sample(.47),(1,1,1,.5))
    def test_inner_transition(self):
        for a,b in zip(self.sample(.495),(.5,.5,.5,.25)):self.assertAlmostEqual(a,b)
    def test_body_threshold_at_half_uses_base_texel(self):self.assertEqual(self.sample(.5),(1,1,1,.5))
    def test_inside_shape_preserves_texel_alpha(self):self.assertEqual(self.sample(.75),(1,1,1,.75))
    def test_vertex_rgb_does_not_retint_outline(self):
        self.assertEqual(self.sample(.47,vertex=(0,0,0,1),particle=(.2,.3,.8,1)),(.2,.3,.8,.5))
    def test_vertex_alpha_still_fades_outline(self):
        self.assertEqual(self.sample(.47,vertex=(1,1,1,.2)),(1,1,1,.1))
    def test_per_particle_outline_alpha_and_material_alpha_multiply(self):
        self.assertEqual(self.sample(.47,particle=(1,1,1,.4)),(1,1,1,.2))
    def test_overbright_changes_rgb_only(self):
        self.assertEqual(self.sample(.47,bright=2),(2,2,2,.5))
if __name__=='__main__':unittest.main(verbosity=2)
