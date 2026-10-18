import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from selfillum import color_value

class SelfillumColors(unittest.TestCase):
    def test_source_vector_representations(self):
        for value in ('1 0.5 2','[1 0.5 2]',(1,.5,2)):
            self.assertEqual(color_value(value),[1,.5,2,1.])
        self.assertEqual(color_value('{255 128 0}'),[1,128/255,0,1])
        self.assertEqual(color_value(.5),[.5,.5,.5,1])
    def test_invalid_color_is_explicit(self):
        for value in ('bad','1 2','1 nan 2'):
            with self.assertRaises(ValueError):color_value(value)
