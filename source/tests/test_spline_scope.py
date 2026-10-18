import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_renderers import spline_ring_enabled

class SplineScopeTests(unittest.TestCase):
    def test_option_does_not_reject_existing_sprite_or_trail_passes(self):
        material={'sfm_particle_material_spline_type':1}
        def definition(*names):return {'modules':{'renderers':[{'function':n,'parameters':{}} for n in names]}}
        self.assertTrue(spline_ring_enabled(definition('render_rope'),material,True))
        for names in ((),('render_animated_sprites',),('render_sprite_trail',),('render_rope','render_animated_sprites')):
            self.assertFalse(spline_ring_enabled(definition(*names),material,True))
        self.assertFalse(spline_ring_enabled(definition('render_rope'),material,False))
        self.assertFalse(spline_ring_enabled(definition('render_rope'),{},True))
