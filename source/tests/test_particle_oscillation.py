import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_bake import appearance

def definition(field,**settings):
    return {'modules':{'operators':[{'function':'Oscillate Scalar Simple','parameters':{'oscillation field':field,**settings}}]}}

class OscillationTests(unittest.TestCase):
    def test_size_matches_integrated_velocity(self):
        settings={'oscillation rate':3,'oscillation frequency':2,'oscillation multiplier':4,'oscillation start phase':.1}
        d=definition(3,**settings)
        # Independent midpoint integration of the specified sinusoidal velocity.
        count=20000;duration=.37;step=duration/count
        expected=10+sum(3*math.sin(.4+8*(i+.5)*step)*step for i in range(count))
        self.assertAlmostEqual(appearance(d,duration,1,10)[0],expected,places=7)

    def test_period_closure_and_birth(self):
        d=definition(3,**{'oscillation rate':4,'oscillation frequency':2,'oscillation multiplier':3})
        self.assertEqual(appearance(d,0,10,10),(10,1))
        self.assertAlmostEqual(appearance(d,math.tau/6,10,10)[0],10)

    def test_zero_frequency_and_bounds(self):
        d=definition(3,**{'oscillation rate':2,'oscillation frequency':0,'oscillation multiplier':2,'oscillation start phase':math.pi/4})
        self.assertAlmostEqual(appearance(d,.5,1,3)[0],4)
        d=definition(7,**{'oscillation rate':-100,'oscillation frequency':0,'oscillation start phase':math.pi/4})
        self.assertEqual(appearance(d,1,2,3),(3,0))

if __name__=='__main__':unittest.main()
