import sys,types,unittest,random
from unittest.mock import patch
from particle_model_scene import Context
from particle_sim import Birth,Segment
from particle_hitbox_lerp import apply

class Binding:
    boxes=[{}]
    def point(self,index,relative,depsgraph):return (0.,0.,0.)
class Scene:
    frame_current=20;frame_subframe=0.
    def __init__(self):self.restores=[]
    def frame_set(self,frame,subframe=0.):
        self.frame_current=frame;self.frame_subframe=subframe;self.restores.append((frame,subframe))
class Cache:
    def __init__(self,scene,mutate=False):self.scene=scene;self.mutate=mutate;self.calls=[]
    def point(self,binding,index,relative,time):
        self.calls.append(time)
        if self.mutate:self.scene.frame_set(99)
        return ((time-10)*2,0.,0.)

class ContextTests(unittest.TestCase):
    def test_original_clock_order_reverse_queries_and_no_redundant_restore(self):
        scene=Scene();cache=Cache(scene)
        context=Context(Binding(),{'position':{},'follow':{'lifetime lerp end':.5}},scene,types.SimpleNamespace(start=10.),60,cache)
        birth=Birth(0,10.2,.2)
        with patch.dict(sys.modules,{'bpy':types.SimpleNamespace(context=types.SimpleNamespace(evaluated_depsgraph_get=lambda:None))}):
            context.birth(birth,random.Random(1),[Segment(10.,11.)],1.)
            actual=context.query(birth,.2)
            expected=previous=(0.,0.,0.)
            for tick in range(1,25):
                age=tick/120.;target=((.2+age)*2,0.,0.)
                expected,previous=apply(expected,previous,target,age=age,end=.5)
            for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=6)
            calls=len(cache.calls)
            earlier=context.query(birth,.1)
            self.assertLess(earlier[0],actual[0]);self.assertEqual(len(cache.calls),calls)
            self.assertEqual(scene.restores,[])
    def test_restores_frame_after_pose_evaluation(self):
        scene=Scene();cache=Cache(scene,True)
        context=Context(Binding(),{'position':{},'follow':{}},scene,types.SimpleNamespace(start=10.),60,cache)
        birth=Birth(0,10.2,.2)
        with patch.dict(sys.modules,{'bpy':types.SimpleNamespace(context=types.SimpleNamespace(evaluated_depsgraph_get=lambda:None))}):
            context.birth(birth,random.Random(1),[Segment(10.,11.)],1.)
            context.query(birth,1/120.)
        self.assertEqual((scene.frame_current,scene.frame_subframe),(20,0.))
        self.assertEqual(scene.restores[-1],(20,0.))
