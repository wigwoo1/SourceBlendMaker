import random
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_bake import appearance,birth_fades


def definition(**parameters):
    return {'modules':{'operators':[{'function':'Alpha Fade Out Random','parameters':parameters}]}}


class FadeOutTests(unittest.TestCase):
    def test_descending_authored_range(self):
        d=definition(**{'fade out time min':.9,'fade out time max':.75})
        class FixedRandom:
            def uniform(self,a,b):return a+.25*(b-a)
        sampled=birth_fades(d,FixedRandom())
        self.assertAlmostEqual(sampled[0],.8625)
        self.assertAlmostEqual(appearance(d,.9,1,3,sampled)[1],.1/.8625)
        for a,b in ((-.1,.5),(.5,-.1),(float('nan'),.5),(.5,float('inf'))):
            with self.assertRaises(ValueError):
                birth_fades(definition(**{'fade out time min':a,'fade out time max':b}),FixedRandom())

    def test_proportional_and_absolute_duration(self):
        d=definition(**{'fade out time min':.4,'fade out time max':.4})
        self.assertEqual(appearance(d,1,4,3),(3,1))
        self.assertAlmostEqual(appearance(d,3.2,4,3)[1],.5)
        d['modules']['operators'][0]['parameters']['proportional 0/1']=False
        self.assertAlmostEqual(appearance(d,3.8,4,3)[1],.5)
        self.assertEqual(appearance(d,4,4,3)[1],0)

    def test_random_duration_is_sampled_once(self):
        d=definition(**{'fade out time min':.2,'fade out time max':.8})
        sampled=birth_fades(d,random.Random(17))
        self.assertTrue(.2<=sampled[0]<=.8)
        self.assertAlmostEqual(appearance(d,.9,1,3,sampled)[1],.1/sampled[0])
        with self.assertRaises(ValueError):appearance(d,.9,1,3)

    def test_easing_and_zero_duration(self):
        d=definition(**{'fade out time min':.4,'fade out time max':.4,'ease in and out':True})
        self.assertAlmostEqual(appearance(d,.9,1,3)[1],.15625)
        d=definition(**{'fade out time min':0,'fade out time max':0})
        self.assertEqual(appearance(d,.99,1,3)[1],1)
        self.assertEqual(appearance(d,1,1,3)[1],0)
