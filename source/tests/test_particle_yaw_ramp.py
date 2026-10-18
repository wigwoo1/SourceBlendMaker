import random,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_yaw import value
from particle_scalar_ramp import settings,step,sample_operators,validate_supported
from particle_roll_history import History

def ramp(field,rate,**extra):return {'function':'Ramp Scalar Linear Random','parameters':{'ramp field':field,'ramp rate min':rate,'ramp rate max':rate,**extra}}
def definition(modules):return {'modules':{'operators':modules}}
class YawRampTests(unittest.TestCase):
    def test_signed_radians_are_unclamped(self):
        s=settings(ramp(12,-2)['parameters'],(0,0,0))
        self.assertEqual(step(s,0,.5,1,.5),-1.)
        self.assertEqual(validate_supported({'ramp field':12})['field'],12)
    def test_independent_from_roll_and_rotation_basic(self):
        d=definition([ramp(4,50),{'function':'Rotation Basic','parameters':{}},ramp(12,2)])
        state={'yaw':.25,'angle':99,'rotation_speed':180}
        self.assertAlmostEqual(value(d,state,.5,1),1.25,places=5)
        self.assertEqual(state['angle'],99)
    def test_backward_and_fractional_queries_preserve_result(self):
        d=definition([ramp(12,3)])
        a={'yaw':0};b={'yaw':0}
        value(d,a,.125,2);value(d,a,.01,2)
        self.assertEqual(value(d,a,.8,2),value(d,b,.8,2))
    def test_multiple_ramps_preserve_window_and_disabled_state(self):
        d=definition([ramp(12,2),ramp(12,-1),ramp(12,500,**{'operator enabled':False})])
        self.assertAlmostEqual(value(d,{'yaw':0},.5,1),.5,places=5)
    def test_initial_yaw_without_ramp_is_unchanged(self):
        self.assertEqual(value(definition([]),{'yaw':1.234},100,200),1.234)
    def test_birth_random_samples_are_reused(self):
        m=ramp(12,1);m['parameters']['ramp rate max']=3
        samples=sample_operators([m],random.Random(4))
        state={'yaw':0,'scalar_oscillations':samples}
        self.assertAlmostEqual(value(definition([m]),state,.5,1),samples[0]['ramp rate min']*.5,places=5)
    def test_unsampled_random_range_is_rejected(self):
        m=ramp(12,1);m['parameters']['ramp rate max']=3
        with self.assertRaisesRegex(ValueError,'sampled'):
            value(definition([m]),{'yaw':0},.5,1)

if __name__=='__main__':unittest.main()
