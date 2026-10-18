import json,math,unittest,random
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_noise import noise,coordinate,f32

tables=[t['values'] for t in json.loads(Path(__file__).resolve().parents[1].joinpath('particle_noise_tables.json').read_text())['tables']]

class NoiseTests(unittest.TestCase):
    def test_lattice_points(self):
        px,py,pz,values=tables
        for x,y,z in ((0,0,0),(1,2,3),(255,254,253)):
            expected=f32(f32(values[pz[(py[(px[x&255]+y)&255]+z)&255]]-.5)*2.)
            self.assertEqual(noise((x,y,z),tables),expected)
    def test_midpoint_is_corner_average(self):
        corners=[noise((x,y,z),tables) for x in (0,1) for y in (0,1) for z in (0,1)]
        self.assertAlmostEqual(noise((.5,.5,.5),tables),sum(corners)/8,places=6)
    def test_periodicity(self):
        for point in ((.25,.75,.5),(12.125,7.25,34.5)):
            self.assertEqual(noise(point,tables),noise(tuple(v+256 for v in point),tables))
    def test_quantization(self):
        self.assertEqual(coordinate(.5),(0,.5))
        # The installed helper reinterprets biased float bits, rather than
        # applying mathematical floor; below 32768 float spacing halves.
        self.assertEqual(coordinate(-.5),(255,0.))
        self.assertEqual(coordinate(-.25),(255,.5))
    def test_bounded_finite(self):
        rng=random.Random(541)
        for _ in range(1000):
            value=noise(tuple(rng.uniform(-100,100) for _ in range(3)),tables)
            self.assertTrue(math.isfinite(value) and -1<=value<=1)
    def test_reject_unvalidated_coordinates(self):
        for value in (float('nan'),float('inf'),1e100):
            with self.assertRaises(ValueError):coordinate(value)

if __name__=='__main__':unittest.main()
