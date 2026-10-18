import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_path import fraction,point,validate

class PathTests(unittest.TestCase):
    def parameters(self,loop=False):return {'bulge':0,'maximum distance':0,'particles to map from start to end':3,'restart behavior (0 = bounce, 1 = loop )':loop}
    def test_bounce_and_loop(self):
        self.assertEqual([fraction(i,self.parameters()) for i in range(6)],[0,.5,1,.5,0,.5])
        self.assertEqual([fraction(i,self.parameters(True)) for i in range(6)],[0,.5,1,0,.5,1])
    def test_world_endpoints(self):
        self.assertEqual(point(1,self.parameters(),(10,20,30),(30,40,50)),(20,30,40))
    def test_unsupported_or_invalid_path_is_reported(self):
        for change in ({'bulge':1},{'maximum distance':2},{'particles to map from start to end':1},{'particles to map from start to end':2.5},{'Save Offset':True}):
            with self.assertRaises(ValueError):validate(self.parameters()|change)
