import unittest,math
from particle_roll_history import History
def ramp(rate):return {'function':'Ramp Scalar Linear Random','parameters':{'ramp field':4,'ramp rate min':rate,'ramp rate max':rate}}
class RollTests(unittest.TestCase):
 def test_negative_rate(self):self.assertEqual(History([ramp(-2)],0,1,tick_step=.25).query(.5),-1)
 def test_basic_rotation_combination(self):
  h=History([{'function':'Rotation Basic','parameters':{}},ramp(2)],.5,1,rotation_speed=180,tick_step=.25)
  self.assertAlmostEqual(h.query(.5),.5+math.pi/2+1,places=6)
 def test_rewind_and_remainder(self):
  h=History([ramp(2)],0,1,tick_step=.25)
  self.assertEqual(h.query(.375),.75);self.assertEqual(h.query(.375),.75)
  self.assertEqual(h.query(.5),1);self.assertEqual(h.query(.25),.5)
 def test_two_ramps_and_disabled(self):
  disabled=ramp(100);disabled['parameters']['operator enabled']=False
  self.assertEqual(History([ramp(2),disabled,ramp(-1)],0,1,tick_step=.25).query(.5),.5)
