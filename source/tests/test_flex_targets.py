import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flex import target_weight

class FlexTargetTests(unittest.TestCase):
    def test_intermediate_shapes(self):
        ranges=((0.,.5,.5,1.),(.5,1.,10.,11.))
        expected=((-1.,(0.,0.)),(.25,(.5,0.)),(.5,(1.,0.)),(.75,(.5,.5)),
                  (1.,(0.,1.)),(2.,(0.,1.)),(10.5,(0.,.5)),(12.,(0.,0.)))
        for value,weights in expected:
            self.assertEqual(tuple(target_weight(value,r) for r in ranges),weights)
    def test_collapsed_ramps(self):
        self.assertEqual(target_weight(.5,(0.,0.,1.,1.)),1.)
        self.assertEqual(target_weight(2.,(0.,0.,1.,1.)),0.)
    def test_rejects_unordered_ranges(self):
        with self.assertRaises(ValueError):target_weight(.5,(0.,1.,.5,2.))
