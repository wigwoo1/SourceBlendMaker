import unittest
from particle_parent_retention import required,retain

class ParentRetentionTests(unittest.TestCase):
    def test_only_enabled_consumers_retain_their_direct_parent(self):
        definitions=[{'parent_instance_id':2,'modules':{'initializers':[
            {'function':'Position From Parent Particles','parameters':{}}]}},
            {'parent_instance_id':3,'modules':{'initializers':[
            {'function':'Position From Parent Particles','parameters':{'operator enabled':False}}]}}]
        self.assertEqual(required(definitions),{2})
        self.assertTrue(retain(2,{2},retain_leaf_contexts=False))
        self.assertFalse(retain(3,{2},retain_leaf_contexts=False))
        self.assertTrue(retain(3,{2},simulation_only=True,retain_leaf_contexts=False))
        self.assertTrue(retain(3,{2}))

    def test_child_cp_writer_keeps_its_own_motion_context(self):
        definitions=[{'instance_id':4,'modules':{'operators':[{
            'function':'Set child control points from particle positions','parameters':{}}]}}]
        self.assertEqual(required(definitions),{4})
