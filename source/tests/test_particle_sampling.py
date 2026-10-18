import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sampling import samples


class ParticleSamplingTests(unittest.TestCase):
    def test_full_quality_keeps_every_frame(self):
        frames,seconds,next_frames=samples([1,2,3],[0.,.1,.2],1)
        self.assertEqual(frames,[1,2,3])
        self.assertEqual(seconds,[0.,.1,.2])
        self.assertEqual(next_frames,{1:2,2:3,3:4})

    def test_fast_modes_keep_terminal_frame_and_hold_to_next_sample(self):
        frames,seconds,next_frames=samples(list(range(1,12)),[v/30 for v in range(11)],4)
        self.assertEqual(frames,[1,5,9,11])
        self.assertEqual(seconds,[0.,4/30,8/30,10/30])
        self.assertEqual(next_frames,{1:5,5:9,9:11,11:12})

    def test_rejects_unsupported_steps_and_mismatched_inputs(self):
        for step in (0,3,16,'bad'):
            with self.subTest(step=step),self.assertRaises(ValueError):samples([1,2],[0.,1.],step)
        with self.assertRaises(ValueError):samples([1],[0.,1.],1)


if __name__=='__main__':unittest.main()
