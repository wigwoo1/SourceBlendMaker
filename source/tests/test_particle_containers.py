import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_containers import controller_reason,empty_container,no_birth_source

class ContainerTests(unittest.TestCase):
    def test_empty_organization_container_skips_simulation(self):
        d={'instance_id':0,'modules':{},'parameters':{}}
        self.assertTrue(empty_container(d))
        self.assertFalse(empty_container(d,{0}))
        d['parameters']['initial_particles']=1
        self.assertFalse(empty_container(d))

    def test_pure_child_container_needs_no_own_geometry(self):
        self.assertIsNone(controller_reason({'modules':{},'children':['smoke','sparks']}))

    def test_parent_controller_names_are_reported(self):
        d={'modules':{'operators':[{'function':'Set Control Point Positions','parameters':{}}],
                      'emitters':[{'function':'emit_continuously','parameters':{}}]}}
        reason=controller_reason(d)
        self.assertIn('operators: Set Control Point Positions',reason)
        self.assertIn('emitters: emit_continuously',reason)

    def test_disabled_controller_does_not_block_children(self):
        self.assertIsNone(controller_reason({'modules':{'operators':[{'function':'Set Control Point Positions','parameters':{'operator enabled':False}}]}}))

    def test_root_without_birth_source_is_an_expected_empty_effect(self):
        d={'instance_id':1,'parent_instance_id':None,'children':[],
           'parameters':{'initial_particles':0},'modules':{'emitters':[],'initializers':[]}}
        self.assertTrue(no_birth_source(d))

    def test_emitter_or_initial_particles_are_not_empty(self):
        d={'instance_id':1,'children':[],'parameters':{'initial_particles':0},
           'modules':{'emitters':[{'function':'emit_continuously','parameters':{}}],'initializers':[]}}
        self.assertFalse(no_birth_source(d))
        d['modules']['emitters']=[];d['parameters']['initial_particles']=1
        self.assertFalse(no_birth_source(d))

    def test_child_and_parent_initialized_definitions_are_not_empty(self):
        d={'instance_id':1,'parent_instance_id':None,'children':['spark'],
           'parameters':{'initial_particles':0},'modules':{'emitters':[],'initializers':[]}}
        self.assertFalse(no_birth_source(d))
        d['children']=[];d['parent_instance_id']=0
        self.assertFalse(no_birth_source(d))
        d['parent_instance_id']=None
        d['modules']['initializers']=[{'function':'Position From Parent Particles','parameters':{}}]
        self.assertFalse(no_birth_source(d))
