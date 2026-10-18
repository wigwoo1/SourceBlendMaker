import unittest
from preview_range import frame_range

class PreviewRangeTests(unittest.TestCase):
    def test_full_and_diagnostic_ranges(self):
        self.assertEqual(frame_range(10000,{}),(1,10000))
        self.assertEqual(frame_range(10000,{'preview_frames':12}),(1,12))
        self.assertEqual(frame_range(10000,{'preview_frames':12,'preview_start_frame':9085}),(9085,12))
        self.assertEqual(frame_range(10,{'preview_frames':12,'preview_start_frame':9}),(9,2))
    def test_invalid_window(self):
        for value in (-1,True,1.5):
            with self.assertRaises(ValueError):frame_range(100,{'preview_frames':12,'preview_start_frame':value})
