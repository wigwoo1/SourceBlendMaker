import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sheet import sequence_lifetime,validate_sequence_lifetime_order,coordinates

class SequenceLifetimeTests(unittest.TestCase):
    def test_material_aware_plan_uses_first_pass_sequence_range(self):
        import copy
        from test_particle_initial_only import definition
        from particle_bake import plan
        sheet={'0':{'frames':[{}]*15},'1':{'frames':[{}]*45}}
        life={'function':'lifetime from sequence','parameters':{'Frames Per Second':30}}
        sequence={'function':'Sequence Random','parameters':{'sequence_min':0,'sequence_max':1}}
        d=definition(1)
        d['modules']['initializers'].extend([life,sequence])
        self.assertEqual(plan(d,sheet)['lifetime_range'],[.5,1.5])
        d['modules']['initializers'].insert(0,d['modules']['initializers'].pop(-2))
        self.assertEqual(plan(d,sheet)['lifetime_range'],[.5,1.5])
    def test_missing_sequence_reports_available_texture_sequences(self):
        # Use valid sequence entries and request a gap between them. Missing
        # out-of-range sequence IDs intentionally clamp to the nearest edge.
        entry={'frames':[{'duration':1,'coordinates':[(0,0,1,1)]}],'duration':1}
        with self.assertRaisesRegex(ValueError,'available sequences: 0, 3'):
            coordinates({'3':entry,'0':entry},1,0,1,{})
    def test_sequence_is_chosen_before_lifetime_is_calculated(self):
        validate_sequence_lifetime_order(['Lifetime Random','Sequence Random','lifetime from sequence'])
        validate_sequence_lifetime_order(['Lifetime Random','lifetime from sequence','Sequence Random'])
        validate_sequence_lifetime_order(['lifetime from sequence','Lifetime Random','Sequence Random'])
    def test_scalar_remap_interaction_remains_rejected(self):
        with self.assertRaisesRegex(ValueError,'order/remap'):
            validate_sequence_lifetime_order(['Lifetime Random','lifetime from sequence','Remap Initial Scalar'])
    def test_selected_sequence_frame_count_and_authored_rate(self):
        sheet={'0':{'frames':[{}]*15},'1':{'frames':[{}]*45}}
        self.assertEqual(sequence_lifetime(sheet,0,{'Frames Per Second':30}),.5)
        self.assertEqual(sequence_lifetime(sheet,1,{'Frames Per Second':30}),1.5)
    def test_missing_rate_uses_installed_default_but_explicit_invalid_rate_fails(self):
        self.assertEqual(sequence_lifetime({'0':{'frames':[{}]*15}},0,{}),.5)
        for rate in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                sequence_lifetime({'0':{'frames':[{}]}},0,{'Frames Per Second':rate})

    def test_missing_frames_is_reported(self):
        for sheet,parameters in (({}, {'Frames Per Second':30}),({'0':{'frames':[]}},{})):
            with self.assertRaises(ValueError):sequence_lifetime(sheet,0,parameters)

if __name__=='__main__':unittest.main()
