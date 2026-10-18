import unittest
from particle_parent_buffer import Snapshot


class ParentBufferTests(unittest.TestCase):
    def test_snapshot_survives_mutation_of_live_source_buffers(self):
        ids=[4,2];current=[[10,0,0],[30,0,0]];previous=[[2,0,0],[14,0,0]]
        snapshot=Snapshot.capture(3,1,ids,current,previous)
        ids.reverse();current[0][0]=999;previous.clear()
        self.assertEqual(snapshot.particle_ids,(4,2))
        self.assertEqual(snapshot.sample(.5,.5,1),((14.,0.,0.),(8.,0.,0.)))

    def test_empty_parent_snapshot_remains_empty(self):
        snapshot=Snapshot.capture(0,1,[],[],[])
        self.assertEqual(snapshot.current,())
        with self.assertRaises(ValueError):snapshot.sample(0,.5)

    def test_duplicate_and_mismatched_identity_buffers_fail(self):
        for ids,current,previous in (([1,1],[(0,0,0)]*2,[(0,0,0)]*2),
                                     ([1],[],[])):
            with self.assertRaises(ValueError):Snapshot.capture(0,0,ids,current,previous)
