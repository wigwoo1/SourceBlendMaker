import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_bake import plan

def definition(count):
    def module(name,p):return {'function':name,'parameters':p}
    return {'parameters':{'initial_particles':count},'modules':{
        'renderers':[module('render_animated_sprites',{})],'emitters':[],
        'initializers':[module('Position Within Sphere Random',{}),
                        module('Lifetime Random',{'lifetime_min':1,'lifetime_max':1}),
                        module('Radius Random',{'radius_min':1,'radius_max':1})],
        'operators':[],'forces':[],'constraints':[]}}

class InitialOnlyTests(unittest.TestCase):
    def test_installed_lifetime_minimum_zero_and_default_rate(self):
        d=definition(0)
        d['modules']['initializers'][1]['parameters']={'lifetime_max':3}
        d['modules']['emitters']=[{'function':'emit_continuously','parameters':{}}]
        result=plan(d)
        self.assertEqual(result['lifetime_range'],[0,3])
        self.assertEqual(result['rate'],100)
        self.assertEqual(d['modules']['initializers'][1]['parameters'],{'lifetime_max':3})
    def test_authored_initial_particles_without_emitter(self):
        result=plan(definition(2))
        self.assertEqual(result['emitter'],'initial_particles_only')
        self.assertEqual(result['initial_particles'],2)
        self.assertEqual(result['rate'],0)

    def test_empty_effect_reports_no_birth_source(self):
        with self.assertRaisesRegex(ValueError,'No emitter or initial particles'):
            plan(definition(0))

    def test_multiple_emitters_share_collection(self):
        d=definition(2)
        d['modules']['emitters']=[{'function':'emit_continuously','parameters':{'emission_rate':1}}]*2
        self.assertEqual(plan(d)['emitter'],'multiple')

    def test_repeated_sequence_initializers_are_applied_in_authored_order(self):
        d=definition(2)
        d['modules']['initializers'] += [
            {'function':'Sequence Random','parameters':{'sequence_min':1,'sequence_max':3}},
            {'function':'Sequence Random','parameters':{'sequence_min':0,'sequence_max':6}},
        ]
        self.assertEqual(plan(d)['emitter'],'initial_particles_only')

    def test_repeated_sequences_with_sequence_readers_are_rejected(self):
        d=definition(2)
        d['modules']['initializers'] += [
            {'function':'Sequence Random','parameters':{'sequence_min':1,'sequence_max':3}},
            {'function':'Sequence Random','parameters':{'sequence_min':0,'sequence_max':6}},
            {'function':'Remap Initial Scalar','parameters':{'input field':9}},
        ]
        with self.assertRaisesRegex(ValueError,'Repeated Sequence Random with sequence readers'):
            plan(d)
