import sys,random,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_random import seed

class InstanceRandomTests(unittest.TestCase):
    def test_first_instance_preserves_existing_stream(self):
        self.assertEqual(seed({'random_seed':7},{'name':'fire','random_instance_index':0}),'7fire')
    def test_repeated_instances_are_distinct_and_repeatable(self):
        descriptor={'random_seed':7}
        streams=[[random.Random(seed(descriptor,{'name':'fire','random_instance_index':i})).random()] for i in range(3)]
        self.assertEqual(len({s[0] for s in streams}),3)
        self.assertEqual(streams[1][0],random.Random(seed(descriptor,{'name':'fire','random_instance_index':1})).random())

if __name__=='__main__':unittest.main()
