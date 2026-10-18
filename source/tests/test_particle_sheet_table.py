import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sheet_table import Table


def entry(clamp=False,durations=(1.,1.),sets=1):
    return {'clamp':clamp,'duration':sum(durations),
            'frames':[{'duration':d,'coordinates':[(float(i+j*10),0,1,1) for j in range(sets)]} for i,d in enumerate(durations)]}


class SheetTableTests(unittest.TestCase):
    def test_interpolates_frames_instead_of_holding_until_next_frame(self):
        table=Table(entry());sample=table.at(256)
        self.assertEqual(sample.current[0],0);self.assertEqual(sample.following[0],1)
        self.assertEqual(sample.blend,.5)

    def test_wrap_and_clamp_have_different_last_frame_behavior(self):
        loop=Table(entry()).at(768);clamp=Table(entry(True)).at(768)
        self.assertEqual((loop.current[0],loop.following[0],loop.blend),(1,0,.5))
        self.assertEqual((clamp.current[0],clamp.following[0],clamp.blend),(1,1,1))

    def test_exact_boundaries_retain_installed_previous_next_representation(self):
        loop=Table(entry());a=loop.at(0);b=loop.at(512)
        self.assertEqual((a.current[0],a.following[0],a.blend),(1,0,1))
        self.assertEqual((b.current[0],b.following[0],b.blend),(0,1,1))

    def test_negative_clamped_clock_selects_last_table_sample(self):
        table=Table(entry(True))
        self.assertEqual(table.at(-1),table.at(1023))
        self.assertEqual(table.sample(-.1,1),table.at(-102))

    def test_clock_is_quantized_to_1024_samples(self):
        table=Table(entry());self.assertEqual(table.sample(.1,1),table.sample(.1001,1))
        self.assertNotEqual(table.sample(.1,1),table.sample(.102,1))
        self.assertEqual(table.at(1024),table.at(0))

    def test_nonuniform_durations_control_interpolation_intervals(self):
        table=Table(entry(durations=(1.,3.)))
        self.assertEqual(table.keys,(0.,256.))
        self.assertEqual(table.at(128).blend,.5)

    def test_preserves_second_coordinate_set_and_ignores_unused_sets(self):
        table=Table(entry(sets=4));sample=table.at(256)
        self.assertEqual((sample.alternate_current[0],sample.alternate_following[0]),(10,11))
        one=Table(entry()).at(256)
        self.assertEqual(one.current,one.alternate_current)

    def test_single_frame_uses_one_constant_sample(self):
        table=Table(entry(durations=(1.,)))
        self.assertEqual(len(table.data),17)
        self.assertEqual(table.sample(30,50),table.at(0))

    def test_declared_duration_follows_installed_integer_conversion(self):
        data=entry();data['duration']=2.9
        self.assertEqual(Table(data).keys,(0.,512.))

    def test_invalid_or_unverified_sequences_fail_explicitly(self):
        for data in (entry(durations=(0.,1.)),{**entry(),'duration':.9},
                     {**entry(),'frames':[]},{**entry(),'duration':float('nan')}):
            with self.assertRaises(ValueError):Table(data)
        with self.assertRaises(ValueError):Table(entry()).sample(float('inf'),1)

    def test_degenerate_source_wrap_interval_is_reported(self):
        with self.assertRaisesRegex(ValueError,'Degenerate sheet wrap interval'):
            Table(entry(durations=(1.,.5)))
