import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from compare_sfm_capture import compare

class Element(dict):name='blink'
class ComparisonTests(unittest.TestCase):
 def setup_fixture(self,value):
  controller=Element(flexWeight=0)
  animation=Element(gameModel={'modelName':'models/test.mdl','globalFlexControllers':[controller]});animation.name='character'
  shot=NS(element=Element(animationSets=[animation]),start=10,value=lambda element,key,time,default:time-10);shot.element.name='shot1'
  session=NS(fps=60,shots=[shot])
  capture={'shot':'shot1','models':[{'name':'character','model_path':'MODELS\\test.mdl','controllers':[{'name':'blink','value':value}]}]}
  return session,capture
 def test_explicit_source_frame_maps_to_native_plus_one(self):
  session,capture=self.setup_fixture(.5);result=compare(session,capture,30)
  self.assertTrue(result['all_captured_controllers_match'])
  self.assertEqual(result['corresponding_blender_shot_frame'],31)
  self.assertEqual(result['source_seconds'],10.5)
 def test_mismatch_is_reported(self):
  session,capture=self.setup_fixture(.7);result=compare(session,capture,30)
  self.assertFalse(result['all_captured_controllers_match'])
  self.assertAlmostEqual(result['mismatches'][0]['difference'],.2)
 def test_incomplete_capture_does_not_pass(self):
  session,capture=self.setup_fixture(.5);capture['errors']=['Some attributes unreadable']
  self.assertFalse(compare(session,capture,30)['all_captured_controllers_match'])
 def test_particle_position_mismatch_is_separate_from_flex(self):
  session,capture=self.setup_fixture(.5)
  cp=Element(position=[1,2,3],orientation=[0,0,0,1]);cp.name='controlPoint0'
  particle=Element(particleSystemType='fog',visible=True,simulating=True,emitting=True,simulationTimeScale=1,randomSeed=4,controlPoints=[cp]);particle.name='Fog21'
  scene=Element(children=[particle]);session.shots[0].element['scene']=scene
  original=session.shots[0].value
  session.shots[0].value=lambda element,key,time,default:element.get(key,default) if key!='flexWeight' else original(element,key,time,default)
  capture['particles']=[{'name':'Fog21','particleSystemType':'fog','visible':True,'simulating':True,'emitting':True,'simulationTimeScale':1,'randomSeed':4,'control_points':[{'name':'controlPoint0','position':[1,2,4]}]}]
  result=compare(session,capture,30)
  self.assertTrue(result['all_captured_controllers_match'])
  self.assertFalse(result['particle_comparison']['all_compared_particle_inputs_match'])
  self.assertEqual(result['particle_comparison']['mismatches'][0]['difference'],1)
  capture['particles'][0]['control_points'][0]['position']=[1,2,3]
  capture['particles'][0]['control_points'][0]['orientation']=[0,0,0,-2]
  self.assertTrue(compare(session,capture,30)['particle_comparison']['all_compared_particle_inputs_match'])
  capture['particles'][0]['control_points'][0]['orientation']=[0,0,1,0]
  result=compare(session,capture,30)['particle_comparison']
  self.assertEqual(result['mismatches'][0]['attribute'],'orientation')
  capture['particles'][0]['control_points'][0]['orientation']=[0,0,1e300,0]
  result=compare(session,capture,30)['particle_comparison']
  self.assertEqual(result['mismatches'][0]['attribute'],'orientation')
  capture['particles'][0]['control_points'][0]['orientation']=[0,0,0,-1e300]
  self.assertTrue(compare(session,capture,30)['particle_comparison']['all_compared_particle_inputs_match'])
  capture['particles'][0]['control_points'][0]['orientation']=[0,0,0,0]
  result=compare(session,capture,30)['particle_comparison']
  self.assertFalse(result['all_compared_particle_inputs_match'])
  self.assertEqual(result['missing'][0]['attribute'],'orientation')
  capture['particles'][0]['control_points'][0]['orientation']=[0,0,0,1]
  cp['scale']=2
  capture['particles'][0]['control_points'][0]['scale']=3
  result=compare(session,capture,30)['particle_comparison']
  self.assertEqual(result['mismatches'][0]['attribute'],'scale')
  capture['particles'][0]['control_points'][0]['scale']=2
  self.assertTrue(compare(session,capture,30)['particle_comparison']['all_compared_particle_inputs_match'])
  capture['particles'][0]['control_points'][0]['scale']=None
  self.assertFalse(compare(session,capture,30)['particle_comparison']['all_compared_particle_inputs_match'])
