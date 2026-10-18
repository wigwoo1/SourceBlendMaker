import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sheet_table import Sample
from particle_dual_sequence_uv import coordinates,scale_parameters,rectangle


class DualSequenceUVTests(unittest.TestCase):
    def sample(self,fraction):
        return Sample((0,0,.5,.5),(.5,0,1,.5),(0,0,1,1),(0,0,1,1),fraction)

    def test_zoom_off_retains_atlas_corners_and_blender_v_orientation(self):
        sample=self.sample(.4)
        expected=((0,.5),(.5,.5),(.5,1),(0,1))
        for zoom in (0,1):self.assertEqual(coordinates(sample,sample,zoom)['primary_current'],expected)
        self.assertEqual(coordinates(sample,sample,1)['secondary_current'],expected)

    def test_source_scale_constants_use_reciprocal_zoom(self):
        self.assertEqual(scale_parameters(4),(.625,.25))
        self.assertEqual(scale_parameters(2),(.75,.5))

    def test_zoom_changes_secondary_frames_without_moving_atlas_center(self):
        sample=self.sample(.5);uvs=coordinates(sample,sample,4)
        self.assertEqual(uvs['primary_current'],rectangle(sample.current))
        for name,center in (('secondary_current',(.25,.75)),('secondary_following',(.75,.75))):
            points=uvs[name]
            self.assertEqual(tuple(sum(p[i] for p in points)/4 for i in range(2)),center)
        self.assertEqual(uvs['secondary_current'][1][0]-uvs['secondary_current'][0][0],.21875)

    def test_continuous_frame_transition_joins_current_and_next_scale(self):
        previous=coordinates(self.sample(0),self.sample(1),4)['secondary_following']
        following=coordinates(self.sample(0),self.sample(0),4)['secondary_current']
        self.assertEqual(previous[1][0]-previous[0][0],following[1][0]-following[0][0])

    def test_invalid_zoom_and_blend_are_explicit(self):
        with self.assertRaises(ValueError):scale_parameters(float('nan'))
        with self.assertRaises(ValueError):coordinates(self.sample(0),self.sample(2),4)
