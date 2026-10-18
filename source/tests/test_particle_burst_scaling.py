import unittest
from particle_burst_scaling import count,settings,sample_time
class BurstScalingTests(unittest.TestCase):
    def test_fraction_truncates_and_negative_clamps(self):
        self.assertEqual(count(8,.49),3)
        self.assertEqual(count(8,-2),0)
        self.assertEqual(count(256,.5),128)
    def test_sample_authored_crossing_inclusive(self):
        self.assertEqual(sample_time(.5,.25,.375),.375)
        self.assertEqual(sample_time(.5,.25,.5),.5)
        self.assertIsNone(sample_time(.5,.1,.375))
    def test_invalid_samples_rejected(self):
        for value in (float('nan'),float('inf'),1e20):
            with self.assertRaises(ValueError):count(256,value)
    def test_settings_reject_snapshot_and_invalid_component(self):
        self.assertEqual(settings({'emission count scale control point':1}),(1,0))
        for p in ({'emission count scale control point':1,'control point with snapshot data':0},
                  {'emission count scale control point':1,'emission count scale control point field':3}):
            with self.assertRaises(ValueError):settings(p)
