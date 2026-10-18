import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from session import shot_frame_count

class ShotBoundaries(unittest.TestCase):
 def test_adjacent_fractional_duration(self):
  shot=SimpleNamespace(start=70.,duration=35.0417)
  following=SimpleNamespace(start=105.0417)
  self.assertEqual(shot_frame_count(shot,24,following),841)
 def test_intentional_overlap_retained(self):
  shot=SimpleNamespace(start=70.,duration=35.0417)
  following=SimpleNamespace(start=104.)
  self.assertEqual(shot_frame_count(shot,24,following),842)
 def test_last_shot_keeps_complete_range(self):
  self.assertEqual(shot_frame_count(SimpleNamespace(start=0.,duration=1.01),24),25)
