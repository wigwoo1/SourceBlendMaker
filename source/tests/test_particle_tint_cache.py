import unittest
from particle_tint_cache import CollectionColor,InitializerCache,History

class TintCacheTests(unittest.TestCase):
    def test_child_reads_historical_parent_and_samples_before_first_parent(self):
        parent=CollectionColor();history=History()
        parent.marker=0
        for time,red in ((1,32),(2,224),(3,64)):
            parent.color=(red,64,128,0);history.record(time,parent)
        child=CollectionColor()
        cache=InitializerCache(child,0,32,lambda p:(16,16,16,0),context_position=(0,0,0))
        self.assertEqual(cache.sample((0,0,0),parent=history.at(.5))[0],16)
        before=(child.marker,child.color,cache.context,cache.query_count)
        self.assertEqual(cache.sample((100,0,0),parent=history.at(1.5))[0],32)
        self.assertEqual((child.marker,child.color,cache.context,cache.query_count),before)
        self.assertEqual(cache.sample((100,0,0),parent=history.at(2.5))[0],224)
        self.assertEqual(history.at(1.5).color[0],32)
    def test_movement_threshold_refreshes_at_boundary(self):
        queries=[]
        def query(p):queries.append(p);return (len(queries),0,0,0)
        cache=InitializerCache(CollectionColor(),0,32,query,context_position=(0,0,0))
        self.assertEqual(cache.sample((0,0,0))[0],1)
        self.assertEqual(cache.sample((31.999,0,0))[0],1)
        self.assertEqual(cache.sample((32,0,0))[0],2)
        self.assertEqual(cache.sample((0,0,0))[0],3)
    def test_snapshot_independence_and_order(self):
        state=CollectionColor();state.marker=0;state.color=(32,0,0,0)
        history=History();history.record(1,state)
        state.color=(64,0,0,0)
        self.assertEqual(history.at(1).color[0],32)
        returned=history.at(1);returned.marker=7
        self.assertEqual(history.at(1).marker,0)
        history.record(1,state)
        self.assertEqual(history.at(1).color[0],64)
        with self.assertRaises(ValueError):history.record(.5,state)
