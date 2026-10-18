"""Independent fixed cases from Valve studio.cpp RunFlexRules eyelid branches."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flex import evaluate

class EyelidRules(unittest.TestCase):
 def model(self,op,eye_index=0):
  controllers=[NS(name='eye',min=-20,max=20),NS(name='unused',min=0,max=1),NS(name='close',min=10,max=30),NS(name='vertical',min=-2,max=2)]
  operations=[NS(op=1,value=eye_index),NS(op=1,value=1),NS(op=1,value=2),NS(op=op,value=3)]
  return NS(flex_names=['lid'],flex_controllers=controllers,flex_rules=[NS(flex_index=0,flex_ops=operations)])
 def test_lower_lid_looks_up_reduces_closure(self):
  mdl=self.model(20)
  for eye,expected in [(-20,.375),(0,.375),(10,.1875),(20,0)]:
   self.assertAlmostEqual(evaluate(mdl,{'eye':eye,'close':20,'vertical':-1})['lid'],expected)
 def test_upper_lid_looks_down_reduces_closure(self):
  mdl=self.model(21)
  for eye,expected in [(-20,0),(-10,.0625),(0,.125),(20,.125)]:
   self.assertAlmostEqual(evaluate(mdl,{'eye':eye,'close':20,'vertical':-1})['lid'],expected)
 def test_no_eye_controller_retains_closure(self):
  self.assertAlmostEqual(evaluate(self.model(20,-1),{'close':20,'vertical':-1})['lid'],.375)
  self.assertAlmostEqual(evaluate(self.model(21,-1),{'close':20,'vertical':-1})['lid'],.125)
if __name__=='__main__':unittest.main()
