import unittest
import numpy as np
from types import SimpleNamespace
from particle_lock_transform import center,bind_sampler,bind_matrix_query,bind_partial_sampler


class Rotation:
    def __init__(self,matrix):self.matrix=matrix
    def inverted(self):return Rotation(self.matrix.T)
    def __matmul__(self,other):
        return Rotation(self.matrix@other.matrix) if isinstance(other,Rotation) else self.matrix@other


class LockTransformTests(unittest.TestCase):
    def test_partial_parent_history_keeps_received_motion_after_detachment(self):
        from particle_sim import Segment,Birth
        from particle_clock_prepared import PreparedInverse
        scene=SimpleNamespace(frame_current=11,frame_subframe=.25,
            view_layers=[SimpleNamespace(depsgraph=None)])
        def frame_set(frame,subframe=0):
            scene.frame_current=frame;scene.frame_subframe=subframe
        scene.frame_set=frame_set
        # Control moves at 10 Source units/sec, represented at world scale .1.
        def evaluated(graph):
            time=(scene.frame_current+scene.frame_subframe-1)/30
            matrix=SimpleNamespace(translation=np.array([time,0.,0.]))
            matrix.copy=lambda:matrix
            return SimpleNamespace(matrix_world=matrix)
        segments=[Segment(0,4)]
        fades={0:(.5,1.)}
        sampler=bind_partial_sampler(
            lambda b,a,l:(np.array([.2,0.,0.]),'red',.5,1),
            SimpleNamespace(evaluated_get=evaluated),scene,segments,fades,512,
            PreparedInverse(segments),0,30,.1,vector=np.array)
        fades[0]=(0.,0.) # The retained context must own its fade settings.
        birth=Birth(0,0,0)
        for age in (2.,4.):
            result=sampler(birth,age,2.)
            # Integral: 10*1 sec + 10*.5 sec = 15 Source units.
            self.assertTrue(np.allclose(result[0],[1.7,0.,0.],atol=1e-10))
            self.assertEqual(result[1:],('red',.5,1))
            self.assertEqual((scene.frame_current,scene.frame_subframe),(11,.25))

    def test_matrix_query_restores_frame_when_control_evaluation_fails(self):
        scene=SimpleNamespace(frame_current=11,frame_subframe=.25,
            view_layers=[SimpleNamespace(depsgraph=None)])
        def frame_set(frame,subframe=0):
            scene.frame_current=frame;scene.frame_subframe=subframe
        scene.frame_set=frame_set
        def fail(graph):raise RuntimeError('failed control evaluation')
        query=bind_matrix_query(SimpleNamespace(evaluated_get=fail),scene,lambda b,a:a,0,30)
        with self.assertRaises(RuntimeError):query(None,.5)
        self.assertEqual((scene.frame_current,scene.frame_subframe),(11,.25))

    def test_bound_sampler_queries_requested_age_and_preserves_appearance(self):
        times=[]
        def matrix_at_age(birth,age):
            times.append(age)
            return SimpleNamespace(translation=np.array([age*10,0.,0.]))
        sampler=bind_sampler(lambda b,a,l:(np.array([2.,0.,0.]),'red',.5,1),
            {0:np.array([1.,0.,0.])},{0:(np.array([0.,0.,0.]),None)},
            matrix_at_age,vector=np.array)
        result=sampler(SimpleNamespace(index=0),.5,1)
        self.assertTrue(np.array_equal(result[0],[7.,0.,0.]))
        self.assertEqual(result[1:],('red',.5,1))
        self.assertEqual(times,[.5])

    def test_collection_previous_buffer_includes_control_motion(self):
        from particle_parent_collection import Collection
        birth=SimpleNamespace(index=0,simulation_time=0)
        sampler=bind_sampler(lambda b,a,l:(np.zeros(3),None,None,None),
            {0:np.zeros(3)},{0:(np.zeros(3),None)},
            lambda b,a:SimpleNamespace(translation=np.array([a*10,0.,0.])),vector=np.array)
        collection=Collection(0,[birth],{0:2},{0:(0,0,0)},sampler,1)
        view=collection.snapshot(.5,.1)
        self.assertEqual(view.current,((5.,0.,0.),))
        self.assertEqual(view.previous,((4.,0.,0.),))

    def test_translation_lock_uses_birth_to_current_delta(self):
        current=SimpleNamespace(translation=np.array([10.,20.,30.]))
        self.assertTrue(np.array_equal(center(np.array([2.,3.,4.]),current,np.array([1.,1.,1.]),None),[11.,22.,33.]))

    def test_rotation_lock_rotates_relative_to_birth_origin(self):
        rotation=Rotation(np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]))
        current=SimpleNamespace(translation=np.array([10.,0.,0.]),to_quaternion=lambda:rotation)
        result=center(np.array([3.,1.,0.]),current,np.array([1.,1.,0.]),Rotation(np.eye(3)),True)
        self.assertTrue(np.array_equal(result,[10.,2.,0.]))
