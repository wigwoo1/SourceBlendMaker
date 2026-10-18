import unittest
from particle_model_history import History

class HistoryTests(unittest.TestCase):
    def test_random_access_is_immutable_and_interpolates_both_buffers(self):
        h=History();position=[0,0,0];h.record(0,position,(-1,0,0));position[0]=99
        h.record(1,(10,0,0),(8,0,0))
        self.assertEqual(h.query(.5),((5.,0.,0.),(3.5,0.,0.)))
        self.assertEqual(h.query(1),((10.,0.,0.),(8.,0.,0.)))
        self.assertEqual(h.query(0),((0.,0.,0.),(-1.,0.,0.)))
        self.assertEqual(len(h.times),2)
    def test_invalid_queries_and_steps_rejected(self):
        h=History();h.record(0,(0,0,0),(0,0,0))
        for age in (-1,1,float('nan')):
            with self.assertRaises(ValueError):h.query(age)
        with self.assertRaises(ValueError):h.record(0,(1,0,0),(1,0,0))
