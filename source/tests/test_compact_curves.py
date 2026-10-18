import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from session import Curve,Clock
from compact_dmx import NumericArray

class CompactCurves(unittest.TestCase):
 def make(self,times,values,types=()):
  return Curve({'log':{'layers':[{'times':times,'values':values,'curvetypes':types}]}},Clock())
 def test_ordered_storage_retained(self):
  times=NumericArray(struct.pack('<3f',0,1,2),'f',lambda x:x[0])
  values=NumericArray(struct.pack('<3f',0,10,20),'f',lambda x:x[0])
  curve=self.make(times,values)
  self.assertIs(curve.layers[0][0],times);self.assertIs(curve.layers[0][1],values)
  self.assertEqual(curve.sample(.5),5)
 def test_unsorted_storage_reordered(self):
  curve=self.make([2.,0.,1.],[20.,0.,10.])
  self.assertEqual(curve.sample(.5),5)
 def test_hold_retained(self):
  curve=self.make([0.,1.,2.],[0.,10.,20.],[3855,1542,0])
  self.assertEqual(curve.sample(.5),0)
  self.assertEqual(curve.sample(1.5),15)
