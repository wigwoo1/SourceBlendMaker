import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_burst import validate_instantaneous_count

class BurstTests(unittest.TestCase):
    def test_unlimited_sentinel_and_explicit_cap(self):
        self.assertEqual(validate_instantaneous_count(300,-1),300)
        self.assertEqual(validate_instantaneous_count(8,8),8)
        self.assertEqual(validate_instantaneous_count(0,0),0)
    def test_spreading_is_not_silently_collapsed(self):
        with self.assertRaisesRegex(ValueError,'Multi-frame'):validate_instantaneous_count(50,8)
    def test_invalid_counts_and_limits(self):
        for count,maximum in ((-1,-1),(1000001,-1),(1,-2)):
            with self.assertRaises(ValueError):validate_instantaneous_count(count,maximum)
