import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from animation_sampling import parse_target_fps,resample_curve


class AnimationSamplingTests(unittest.TestCase):
    def test_sixty_to_thirty_keeps_every_other_sample_and_endpoints(self):
        frames=list(range(1,62))
        values=[float(frame*2) for frame in frames]
        sampled_frames,sampled_values=resample_curve(frames,values,60,30)
        self.assertEqual(sampled_frames,list(map(float,range(1,62,2))))
        self.assertEqual(sampled_values,[float(frame*2) for frame in range(1,62,2)])
        self.assertEqual(sampled_frames[0],frames[0])
        self.assertEqual(sampled_frames[-1],frames[-1])

    def test_non_integer_rate_uses_fractional_timing_and_linear_values(self):
        frames=list(range(1,62))
        values=[float(frame-1) for frame in frames]
        sampled_frames,sampled_values=resample_curve(frames,values,60,24)
        self.assertEqual(len(sampled_frames),25)
        self.assertAlmostEqual(sampled_frames[1],3.5)
        self.assertAlmostEqual(sampled_values[1],2.5)
        self.assertEqual(sampled_frames[-1],61.0)
        self.assertEqual(sampled_values[-1],60.0)

    def test_zero_or_source_rate_keeps_all_keys(self):
        frames=[1,2,3,4]
        values=[0,2,4,6]
        self.assertEqual(resample_curve(frames,values,60,0),([1.,2.,3.,4.],[0.,2.,4.,6.]))
        self.assertEqual(resample_curve(frames,values,60,60),([1.,2.,3.,4.],[0.,2.,4.,6.]))

    def test_rate_validation(self):
        self.assertEqual(parse_target_fps('30'),30.0)
        self.assertEqual(parse_target_fps('0'),0.0)
        for invalid in ('', 'abc', '-1', '241', 'nan', 'inf'):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                parse_target_fps(invalid)


if __name__=='__main__':
    unittest.main()
