import unittest
from particle_parent_graph import ordered


class ParentGraphTests(unittest.TestCase):
    def test_deep_graph_avoids_python_recursion_limit(self):
        definitions=[{'instance_id':i,'parent_instance_id':i-1 if i else None} for i in reversed(range(10000))]
        self.assertEqual([d['instance_id'] for d in ordered(definitions)],list(range(10000)))

    def test_repeated_effect_names_keep_distinct_parent_instances(self):
        definitions=[{'instance_id':3,'parent_instance_id':2,'name':'smoke'},
                     {'instance_id':1,'parent_instance_id':0,'name':'smoke'},
                     {'instance_id':2,'parent_instance_id':None,'name':'fire'},
                     {'instance_id':0,'parent_instance_id':None,'name':'fire'}]
        self.assertEqual([d['instance_id'] for d in ordered(definitions)],[2,3,0,1])
        self.assertIs(ordered(definitions)[0],definitions[2])

    def test_rendererless_parent_is_retained(self):
        parent={'instance_id':0,'parent_instance_id':None,'modules':{'renderers':[]}}
        child={'instance_id':1,'parent_instance_id':0}
        self.assertEqual(ordered([child,parent]),[parent,child])

    def test_invalid_dependencies_are_rejected(self):
        for definitions in ([{'instance_id':0,'parent_instance_id':1}],
                            [{'instance_id':0},{'instance_id':0}],
                            [{'instance_id':0,'parent_instance_id':1},{'instance_id':1,'parent_instance_id':0}]):
            with self.assertRaises(ValueError):ordered(definitions)
