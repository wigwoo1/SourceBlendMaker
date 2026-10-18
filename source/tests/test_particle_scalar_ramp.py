import unittest,random
from particle_scalar_ramp import sample_operators,validate_radius,settings
from particle_radius_remap import radius
def m(name,p):return {'function':name,'parameters':p}
class RampIntegrationTests(unittest.TestCase):
 def test_authored_overwrite_order(self):
  ramp=m('Ramp Scalar Linear Random',{'ramp rate min':2,'ramp rate max':2})
  scale=m('Radius Scale',{'start_time':0,'end_time':1,'radius_start_scale':3,'radius_end_scale':3})
  self.assertEqual(radius([ramp,scale],.5,1,1,0,step=.25),3)
  self.assertEqual(radius([scale,ramp],.5,1,1,0,step=.25),3.5)
 def test_birth_samples_and_unsampled_rejection(self):
  module=m('Ramp Scalar Linear Random',{'ramp rate min':1,'ramp rate max':3})
  samples=sample_operators([module],random.Random(4))
  self.assertEqual(samples[0]['ramp rate min'],samples[0]['ramp rate max'])
  with self.assertRaisesRegex(ValueError,'birth-sampled'):radius([module],.5,1,1,0)
 def test_disabled_preserves_random_stream(self):
  rng=random.Random(4);expected=random.Random(4).random()
  self.assertEqual(sample_operators([m('Ramp Scalar Linear Random',{'operator enabled':False})],rng),{})
  self.assertEqual(rng.random(),expected)
 def test_reject_unintegrated_context(self):
  with self.assertRaises(ValueError):validate_radius({'ramp field':4})
  with self.assertRaises(ValueError):validate_radius({'operator start fadein':1})
 def test_sampling_preserves_original_window_gate(self):
  class ZeroRandom:
   def random(self):return 0.
  module=m('Ramp Scalar Linear Random',{'start time min':0,'start time max':.5,'end time min':1,'end time max':2})
  sampled=sample_operators([module],ZeroRandom())[0]
  self.assertTrue(settings(sampled,(0,0,0))['gated'])
