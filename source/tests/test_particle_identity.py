import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_identity import tag

class IdentityTests(unittest.TestCase):
    def test_repeated_child_instances_remain_distinct(self):
        a={};b={}
        tag(a,{'instance_id':1,'parent_instance_id':0,'random_instance_index':0})
        tag(b,{'instance_id':2,'parent_instance_id':0,'random_instance_index':1})
        self.assertNotEqual(a['sfm_particle_instance_id'],b['sfm_particle_instance_id'])
        self.assertEqual(a['sfm_particle_parent_instance_id'],b['sfm_particle_parent_instance_id'])
        self.assertNotEqual(a['sfm_particle_random_instance_index'],b['sfm_particle_random_instance_index'])

    def test_root_and_renderer_defaults_are_serializable_integers(self):
        obj={};tag(obj,{})
        self.assertEqual(obj,{'sfm_particle_instance_id':-1,'sfm_particle_parent_instance_id':-1,
                             'sfm_particle_random_instance_index':0,'sfm_particle_renderer_pass':0})
        tag(obj,{'instance_id':0,'parent_instance_id':None,'renderer_pass_index':2})
        self.assertEqual(obj['sfm_particle_instance_id'],0)
        self.assertEqual(obj['sfm_particle_parent_instance_id'],-1)
        self.assertEqual(obj['sfm_particle_renderer_pass'],2)
