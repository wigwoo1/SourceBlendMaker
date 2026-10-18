import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace as S
from flex import evaluate

class FlexRangeTests(unittest.TestCase):
    def model(self,low,high):
        return S(flex_names=['result'],flex_controllers=[S(name='control',min=low,max=high)],flex_rules=[S(flex_index=0,flex_ops=[S(op=2,value=0)])])
    def test_clamps_unsigned_controller(self):
        model=self.model(0.,1.)
        self.assertEqual(evaluate(model,{'control':-.14})['result'],0.)
        self.assertEqual(evaluate(model,{'control':1.2})['result'],1.)
    def test_signed_controller_preserves_negative(self):
        self.assertEqual(evaluate(self.model(-1.,1.),{'control':-.14})['result'],-.14)
