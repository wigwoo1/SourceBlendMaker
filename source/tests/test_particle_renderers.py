import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_renderers import passes
from particle_random import seed
from test_particle_initial_only import definition
from particle_bake import plan

class RenderPassTests(unittest.TestCase):
    def test_render_parameters_separate_but_simulation_identity_shared(self):
        d=definition(2);d['name']='paired effect'
        d['modules']['renderers'].append({'function':'render_sprite_trail','parameters':{'max length':4}})
        result=passes(d)
        self.assertEqual(len(result),2)
        self.assertEqual([r['renderer_pass_index'] for r in result],[0,1])
        self.assertIs(result[0]['modules']['initializers'],result[1]['modules']['initializers'])
        self.assertEqual(seed({'random_seed':4},result[0]),seed({'random_seed':4},result[1]))
        self.assertEqual(len(d['modules']['renderers']),2)
        self.assertEqual(plan(d)['renderer'],'multiple')

    def test_unsupported_pass_is_not_discarded(self):
        d=definition(2)
        d['modules']['renderers'].append({'function':'Render Deferred Light','parameters':{}})
        with self.assertRaisesRegex(ValueError,'Unsupported renderers'):plan(d)

    def test_disabled_pass_does_not_duplicate_geometry(self):
        d=definition(2)
        d['modules']['renderers'].append({'function':'render_sprite_trail','parameters':{'operator enabled':False}})
        self.assertEqual(passes(d),[d])
