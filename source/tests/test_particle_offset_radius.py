import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sprite_state import offset_radius

class OffsetRadiusTests(unittest.TestCase):
    def test_radius_remap_before_offset_applies_but_later_remap_does_not(self):
        fields={3:3.,8:0.}
        remap={'function':'Remap Initial Scalar','parameters':{'input field':8,'output field':3,'output minimum':5,'output maximum':5}}
        offset={'function':'Position Modify Offset Random','parameters':{}}
        self.assertEqual(offset_radius(fields,[remap,offset]),5.)
        self.assertEqual(offset_radius(fields,[offset,remap]),3.)

    def test_disabled_remap_and_offset_do_not_change_prefix(self):
        fields={3:2.,8:0.}
        modules=[{'function':'Position Modify Offset Random','parameters':{'operator enabled':False}},
                 {'function':'Remap Initial Scalar','parameters':{'operator enabled':False}}]
        self.assertEqual(offset_radius(fields,modules),2.)

    def test_repeated_offsets_use_each_preceding_radius_remap(self):
        fields={3:1.,8:0.}
        remap_two={'function':'Remap Initial Scalar','parameters':{'input field':8,'output field':3,'output minimum':2,'output maximum':2}}
        offset={'function':'Position Modify Offset Random','parameters':{}}
        remap_three={'function':'Remap Initial Scalar','parameters':{'input field':8,'output field':3,'output minimum':3,'output maximum':3}}
        modules=[remap_two,offset,remap_three,offset]
        self.assertEqual(offset_radius(fields,modules,stop_index=1),2.)
        self.assertEqual(offset_radius(fields,modules,stop_index=3),3.)

    def test_invalid_radius_is_rejected(self):
        for value in (-1.,float('nan'),float('inf')):
            with self.assertRaises(ValueError):offset_radius({3:value},[])
