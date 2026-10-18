import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_control import lock_settings

class RotationLockTests(unittest.TestCase):
    def test_full_rotation_and_translation_locks(self):
        self.assertEqual(lock_settings({}), (0,False))
        self.assertEqual(lock_settings({'control_point_number':3,'lock rotation':True}), (3,True))

    def test_partial_locks_remain_explicit(self):
        for parameters in ({'distance fade range':1},{'start_fadeout_min':.5},{'end_fadeout_max':.8}):
            with self.assertRaisesRegex(ValueError,'Partial'):lock_settings(parameters)

    def test_invalid_control_point(self):
        for index in (-1,64,.5,float('nan'),float('inf')):
            with self.assertRaisesRegex(ValueError,'control point'):lock_settings({'control_point_number':index})
