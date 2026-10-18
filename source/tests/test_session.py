import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from session import Clock,Curve,Shot,expression,quat_slerp
from flex import evaluate
from audio import envelope


class Tests(unittest.TestCase):
    def test_floor_lerp_discrete_values(self):
        for value,expected in ((0,0),(.249,0),(.25,1),(.999,3),(1,4)):
            self.assertEqual(expression('floor(lerp(value, lo, hi))',{'value':value,'lo':0,'hi':4}),expected)
        self.assertEqual(expression('floor(value)',{'value':-.1}),-1)
        with self.assertRaises(ValueError):expression('math.floor(value)',{'value':1})

    def test_flex_division_source_threshold(self):
        for denominator,expected in ((-2,0),(0,0),(.0001,0),(.0002,10000),(2,1)):
            operations=[NS(op=1,value=2),NS(op=1,value=denominator),NS(op=7,value=0)]
            mdl=NS(flex_names=['result'],flex_controllers=[],flex_rules=[NS(flex_index=0,flex_ops=operations)])
            self.assertEqual(evaluate(mdl,{})['result'],expected)
    def test_channel_modes_ignore_stale_logs(self):
        class Element(dict):
            id='target';type='DmeTransform'
        target=Element(position=17.)
        source=Element(position=5.);source.id='source'
        channel={'mode':1,'fromElement':source,'fromAttribute':'position','log':{'layers':[{'times':[0.,1.],'values':[100.,200.]}]}}
        shot=Shot.__new__(Shot);shot.connections={};shot.curves={('target','position',0):Curve(channel,Clock())}
        self.assertEqual(shot.value(target,'position',.5),5.)
        channel['mode']=0;self.assertEqual(shot.value(target,'position',.5),17.)
        channel['mode']=3;self.assertEqual(shot.value(target,'position',.5),150.)
        channel['mode']=2;self.assertEqual(shot.value(target,'position',.5),5.)

    def test_material_connection_samples_expression_input(self):
        class Element(dict):pass
        source=Element(value=0.,lo=0.,hi=2.,result=-9.,expr='lerp(value, lo, hi)')
        source.id='expression';source.type='DmeExpressionOperator'
        target=Element(color=-9.);target.id='material';target.type='DmeMaterial'
        channel={'mode':3,'log':{'layers':[{'times':[0.,1.],'values':[0.,1.]}]}}
        shot=Shot.__new__(Shot);shot.curves={('expression','value',0):Curve(channel,Clock())}
        shot.connections={('material','color',0):{'element':source,'attribute':'result','index':0}}
        self.assertEqual(shot.value(target,'color',.25),.5)
        self.assertEqual(shot.value(target,'color',.75),1.5)

    def test_constant_proof_rejects_live_connections_and_varying_logs(self):
        class Element(dict):
            id='target';type='DmeTransform'
        target=Element(position=[1.,2.,3.])
        shot=Shot.__new__(Shot);shot.curves={};shot.connections={}
        self.assertTrue(shot.is_constant(target,'position'))
        channel={'mode':3,'log':{'layers':[{'times':[0.,1.],'values':[[1.,2.,3.],[1.,2.,3.]]}]}}
        shot.curves[('target','position',0)]=Curve(channel,Clock())
        self.assertTrue(shot.is_constant(target,'position'))
        channel['log']['layers'][0]['values'][1]=[1.,2.,4.]
        self.assertFalse(shot.is_constant(target,'position'))
        shot.connections[('target','position',0)]={'element':target,'attribute':'position'}
        self.assertFalse(shot.is_constant(target,'position'))

    def test_explicit_hold_and_linear_curves(self):
        for code,expected in [(3855,10.),(1542,15.)]:
            curve=Curve({'log':{'layers':[{'times':[0.,1.],'values':[10.,20.],'curvetypes':[code,code]}]}},Clock())
            self.assertEqual(curve.sample(.5),expected)
            self.assertEqual(curve.sample(1.),20.)
            self.assertEqual(curve.issues,[])
        curve=Curve({'log':{'curveinfo':{'defaultCurveType':3855},'layers':[{'times':[0.,1.],'values':[10.,20.]}]}},Clock())
        self.assertEqual(curve.sample(.5),10.)
    def test_sound_envelope(self):
        self.assertEqual(envelope(0,4,1,1,.8),0)
        self.assertAlmostEqual(envelope(.5,4,1,1,.8),.4)
        self.assertAlmostEqual(envelope(2,4,1,1,.8),.8)
        self.assertAlmostEqual(envelope(3.5,4,1,1,.8),.4)
        self.assertEqual(envelope(4,4,1,1,.8),0)
    def test_nested_timing(self):
        outer=Clock().child({'timeFrame':{'start':10,'offset':2,'scale':2}})
        inner=outer.child({'timeFrame':{'start':4,'offset':1,'scale':.5}})
        self.assertAlmostEqual(inner.global_time(3),13)
        self.assertAlmostEqual(inner.local_time(13),3)

    def test_curve_sampling(self):
        curve=Curve({'log':{'layers':[{'times':[0.,2.],'values':[0.,10.]}]}},Clock(5,2))
        self.assertEqual(curve.sample(7),5)
        self.assertEqual(curve.sample(0),0)
        self.assertEqual(curve.sample(15),10)

    def test_quaternion_shortest_path(self):
        q=quat_slerp([0,0,0,1],[0,0,0,-1],.5)
        self.assertAlmostEqual(q[3],1)
        self.assertAlmostEqual(sum(x*x for x in q),1)

    def test_expressions_and_no_code_execution(self):
        self.assertEqual(expression('lerp(value, lo, hi)',{'value':.5,'lo':10,'hi':120}),65)
        with self.assertRaises(ValueError):expression('__import__("os").system("whoami")',{})

    def test_flex_operand_order_and_dominate(self):
        def op(kind,value=0):return NS(op=kind,value=value)
        mdl=NS(flex_names=['subtract','divide','dominate'],flex_controllers=[],flex_rules=[
            NS(flex_index=0,flex_ops=[op(1,8),op(1,2),op(5)]),
            NS(flex_index=1,flex_ops=[op(1,8),op(1,2),op(7)]),
            NS(flex_index=2,flex_ops=[op(1,.8),op(1,.5),op(1,.2),op(19,2)])])
        result=evaluate(mdl,{})
        self.assertEqual(result['subtract'],6)
        self.assertEqual(result['divide'],4)
        self.assertAlmostEqual(result['dominate'],.72)


if __name__=='__main__':unittest.main()
