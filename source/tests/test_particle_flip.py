import random,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sprite_state import sample_yaw_flip,sprite_uvs

class ParticleFlipTests(unittest.TestCase):
    def test_atlas_rectangle_preserved(self):
        rect=[(.2,.3),(.4,.3),(.4,.8),(.2,.8)]
        flipped=sprite_uvs(rect,True)
        self.assertEqual(set(flipped),set(rect))
        self.assertGreater(flipped[0][0],flipped[1][0])
        self.assertEqual(sprite_uvs(flipped,True),rect)

    def test_probabilities_and_invalid_values(self):
        rng=random.Random(9)
        self.assertFalse(sample_yaw_flip({'Flip Percentage':0},rng))
        self.assertTrue(sample_yaw_flip({'Flip Percentage':1},rng))
        for value in (-1,2,float('nan')):
            with self.assertRaises(ValueError):sample_yaw_flip({'Flip Percentage':value},rng)

if __name__=='__main__':unittest.main()
