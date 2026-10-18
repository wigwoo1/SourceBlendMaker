import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datamodel
from particles import Definitions

class ChildDefinitionsTests(unittest.TestCase):
    def test_shared_child_keeps_each_instance_delay_and_parent(self):
        dm=datamodel.DataModel('test',1)
        system=dm.add_element('system','DmeParticleSystem');root=dm.add_element('root');child=dm.add_element('shared')
        links=[]
        for i,delay in enumerate((.2,.8)):
            link=dm.add_element('link'+str(i));link['child']=child;link['delay']=delay;link['group id']=i+7;links.append(link)
        root['children']=datamodel.make_array(links,datamodel.Element);system['particleSystemDefinition']=root
        result=Definitions(None).describe(system)['definitions']
        self.assertEqual(len(result),3)
        self.assertEqual([d['child_delay'] for d in result[1:]],[.2,.8])
        self.assertEqual([d['parent_instance_id'] for d in result[1:]],[0,0])
        self.assertEqual([d['instance_id'] for d in result],[0,1,2])
        self.assertEqual([d['random_instance_index'] for d in result[1:]],[0,1])
        self.assertEqual([d['child_link_parameters']['group id'] for d in result[1:]],[7,8])

    def test_cycle_is_explicitly_reported(self):
        dm=datamodel.DataModel('test',1);system=dm.add_element('system','DmeParticleSystem');root=dm.add_element('root');link=dm.add_element('link')
        link['child']=root;root['children']=datamodel.make_array([link],datamodel.Element);system['particleSystemDefinition']=root
        with self.assertRaisesRegex(ValueError,'Cyclic particle child graph'):Definitions(None).describe(system)

    def test_nested_delay_and_end_cap_inheritance(self):
        dm=datamodel.DataModel('test',1)
        system=dm.add_element('system','DmeParticleSystem')
        parent=dm.add_element('parent');child=dm.add_element('child');grandchild=dm.add_element('grandchild')
        first=dm.add_element('first');first['child']=child;first['delay']=.6;first['end cap effect']=True
        second=dm.add_element('second');second['child']=grandchild;second['delay']=.7
        parent['children']=datamodel.make_array([first],datamodel.Element)
        child['children']=datamodel.make_array([second],datamodel.Element)
        system['particleSystemDefinition']=parent
        result=Definitions(None).describe(system)['definitions']
        self.assertEqual(result[0]['child_delay'],0)
        self.assertAlmostEqual(result[2]['child_delay'],1.3)
        self.assertTrue(result[1]['end_cap_effect'])
        self.assertTrue(result[2]['end_cap_effect'])

if __name__=='__main__':unittest.main()
