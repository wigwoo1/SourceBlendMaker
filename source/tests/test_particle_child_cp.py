import unittest
from types import SimpleNamespace as NS
from particle_child_cp import History,settings,updates
from particle_parent_buffer import Snapshot


def snapshot(time,points,ids=None):
    return Snapshot.capture(0,time,range(len(points)) if ids is None else ids,points,points)


class ChildControlPointTests(unittest.TestCase):
    def test_active_buffer_order_and_source_units_are_preserved(self):
        config=settings({'First control point to set':3,'first particle to copy':1,'# of control points to set':8})
        source=snapshot(0,[(10,0,0),(20,1,2),(30,3,4)],[7,2,9])
        self.assertEqual(updates(config,source),{3:(20.,1.,2.),4:(30.,3.,4.)})

    def test_installed_cp_cap_and_clamp(self):
        config=settings({'First control point to set':999,'# of control points to set':99})
        self.assertEqual(updates(config,snapshot(0,[(1,2,3),(4,5,6)])),{63:(1.,2.,3.)})
        self.assertEqual(settings({'First control point to set':-4})['first_control_point'],0)
        self.assertEqual(updates(settings({'# of control points to set':-1}),snapshot(0,[(1,2,3)])),{})

    def test_blender_bridge_only_declares_control_points_that_can_be_written(self):
        from particle_child_cp_blender import overlay
        context=NS(instance_id=0,births=[object()]*3,snapshot=lambda *_:None,segments=[])
        descriptor={'control_points':[{'id':'origin'}]};origin=object()
        points,controls=overlay(context,settings({'# of control points to set':35}),descriptor,
            {'origin':origin},None,0,24,.0254,lambda _:None)
        self.assertEqual(len(points),3)
        self.assertEqual(len(controls),3)
        self.assertEqual(len(descriptor['control_points']),1)

    def test_unwritten_cps_and_dead_parent_keep_previous_assignment(self):
        def provider(time,step):
            if time<1:return snapshot(time,[(time,0,0),(10,0,0)])
            if time<2:return snapshot(time,[(20,0,0)])
            return snapshot(time,[])
        history=History(settings({'# of control points to set':2}),provider,step=.5)
        self.assertEqual(history.query(.5),{0:(.5,0.,0.),1:(10.,0.,0.)})
        self.assertEqual(history.query(2.5),{0:(20.,0.,0.),1:(10.,0.,0.)})
        self.assertEqual(history.query(0),{0:(0.,0.,0.),1:(10.,0.,0.)})

    def test_query_order_does_not_change_state_or_repeat_parent_queries(self):
        calls=[]
        def provider(time,step):
            calls.append(time)
            return snapshot(time,[(time,0,0)] if time>=.5 else [])
        history=History(settings({}),provider,step=.25)
        self.assertEqual(history.query(1)[0],(1.,0.,0.))
        first_calls=list(calls)
        self.assertEqual(history.query(.1),{})
        self.assertEqual(history.query(.6)[0],(.5,0.,0.))
        self.assertEqual(calls,first_calls)
        self.assertEqual(first_calls,[0.,.25,.5,.75,1.])

    def test_group_id_is_legacy_metadata_not_a_filter_in_installed_build(self):
        self.assertEqual(updates(settings({'Group ID to affect':8}),snapshot(0,[(4,5,6)])),{0:(4.,5.,6.)})
        self.assertEqual(settings({'operator time strength random scale max':1.})['count'],1)

    def test_unsupported_orientation_timing_and_invalid_indices_fail_closed(self):
        for params in ({'set orientation':True},{'operator end fadeout':1},
                       {'first particle to copy':-1},{'first particle to copy':.5},
                       {'First control point to set':True},{'unknown field':1},
                       {'operator time strength random scale max':2.}):
            with self.subTest(params=params),self.assertRaises(ValueError):settings(params)
