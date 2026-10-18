import unittest
from particle_validation import annotate,converted

class ValidationTests(unittest.TestCase):
    def test_rendererless_parent_success_is_not_render_evidence(self):
        r=annotate(dict(rendered=False,simulation_only=True,simulated=True))
        self.assertTrue(converted(r))
        self.assertEqual(r['validation']['stage'],'parent_simulation_baked')
        self.assertFalse(r['validation']['final_image_render_verified'])
        self.assertFalse(r['validation']['source_visual_parity_verified'])

    def test_partial_simulation_with_failure_stays_failed(self):
        r=annotate(dict(rendered=False,simulation_only=True,simulated=True,reason='unsupported history'))
        self.assertFalse(converted(r))
        self.assertEqual(r['validation']['stage'],'conversion_failed')

    def test_hidden_conversion_is_not_render_evidence(self):
        r=annotate(dict(rendered=True,visible_sample_count=0))
        self.assertEqual(r['validation']['stage'],'hidden_at_requested_samples')
        self.assertFalse(r['validation']['final_image_render_verified'])
    def test_nondegenerate_bake_is_not_visual_parity(self):
        r=annotate(dict(rendered=True,renderable_geometry_generated=True))
        self.assertEqual(r['validation']['stage'],'nondegenerate_geometry_baked')
        self.assertFalse(r['validation']['source_visual_parity_verified'])
    def test_failure_wins_over_partial_geometry(self):
        r=annotate(dict(rendered=False,geometry_generated=True))
        self.assertEqual(r['validation']['stage'],'conversion_failed')
