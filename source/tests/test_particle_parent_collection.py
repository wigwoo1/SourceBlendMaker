import unittest
from types import SimpleNamespace
from particle_parent_collection import Collection


class ParentCollectionTests(unittest.TestCase):
    def collection(self):
        births=[SimpleNamespace(index=3,simulation_time=0),SimpleNamespace(index=7,simulation_time=1)]
        return Collection(2,births,{3:2,7:3},{3:(10,0,0),7:(20,0,0)},
            lambda b,age,life:((age*2,0,0),None,None,None),.5)

    def test_clock_lifetimes_and_source_unit_conversion(self):
        view=self.collection().snapshot(1.5,.5)
        self.assertEqual(view.particle_ids,(3,7))
        self.assertEqual(view.current,((26.,0.,0.),(42.,0.,0.)))
        self.assertEqual(view.previous,((24.,0.,0.),(40.,0.,0.)))

    def test_dead_parent_is_removed_at_lifetime_boundary(self):
        self.assertEqual(self.collection().snapshot(2,.5).particle_ids,(7,))
        self.assertEqual(self.collection().snapshot(4,.5).particle_ids,())

    def test_unborn_parent_is_not_present(self):
        self.assertEqual(self.collection().snapshot(.5,.5).particle_ids,(3,))

    def test_previous_query_is_clamped_to_birth(self):
        self.assertEqual(self.collection().snapshot(1.1,1).previous[1],(40.,0.,0.))
