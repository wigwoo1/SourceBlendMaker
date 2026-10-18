import importlib.util,unittest,copy
from pathlib import Path
from types import SimpleNamespace as NS
spec=importlib.util.spec_from_file_location('capture',Path(__file__).resolve().parents[1]/'diagnostics/sourceblendmaker_capture.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Element(NS):
 def GetName(self):return self.name
class Material(Element):
 def iterAttrs(self):
  return [NS(GetName=lambda:'$color2',GetType=lambda:8)]
class CaptureTests(unittest.TestCase):
 def test_capture_retains_pose_and_rig_attributes(self):
  material=Material(name='body',mtlName='models/test/body');setattr(material,'$color2',[1,.5,0])
  model=Element(name='model',modelName='models/test.mdl',flexnames=['smile'],flexWeights=[.7],
                globalFlexControllers=[Element(name='blink',flexWeight=.4)],
                bones=[Element(name='head',position=[1,2,3],orientation=[0,0,0,1])],materials=[material],rig_locked=True)
  before=copy.deepcopy(model)
  shot=Element(name='shot1',animationSets=[Element(name='character',gameModel=model)],camera=Element(name='camera1',fieldOfView=45,transform=Element(position=[1,2,3],orientation=[0,0,0,1])))
  result=module.capture(NS(GetCurrentShot=lambda:shot),'2578')
  self.assertEqual(result['errors'],[])
  self.assertEqual(result['models'][0]['controllers'][0]['value'],.4)
  self.assertEqual(result['models'][0]['materials'][0]['attributes'][0]['value'],[1,.5,0])
  self.assertEqual(model,before)
  self.assertEqual(result['frame_label'],'2578')
  self.assertEqual(result['shot_camera']['fieldOfView'],45)
 def test_missing_active_shot_is_explicit(self):
  with self.assertRaises(ValueError):module.capture(NS(GetCurrentShot=lambda:None),'609')
 def test_mainmenu_selected_shot_fallback(self):
  shot=Element(name='shot1',animationSets=[])
  result=module.capture(NS(GetCurrentShot=lambda:None),'2578',NS(GetSelectedShots=lambda:[shot]))
  self.assertEqual(result['shot'],'shot1')
  self.assertEqual(result['shot_lookup'],'sfmClipEditor.GetSelectedShots')
 def test_multiple_selected_shots_are_rejected(self):
  with self.assertRaises(ValueError):module.capture(NS(GetCurrentShot=lambda:None),'2578',NS(GetSelectedShots=lambda:[Element(name='a'),Element(name='b')]))
 def test_particle_capture_retains_local_controls_and_ancestors(self):
  cp=Element(name='controlPoint0',position=[255,0,0],orientation=[0,0,0,1])
  particle=Element(name='aura',particleSystemType='aura1_spikes2',visible=True,simulating=False,emitting=True,simulationTimeScale=2,randomSeed=7,controlPoints=[cp],children=[],transform=Element(name='auraTransform',position=[1,2,3],orientation=[0,0,0,1]))
  scene=Element(name='scene',children=[particle],transform=Element(name='sceneTransform',position=[10,0,0],orientation=[0,0,0,1]))
  before=copy.deepcopy(scene)
  result=module.capture(NS(GetCurrentShot=lambda:Element(name='shot1',animationSets=[],scene=scene)),'609')
  self.assertEqual(result['errors'],[])
  self.assertEqual(len(result['particles']),1)
  record=result['particles'][0]
  self.assertEqual(record['control_points'][0]['position'],[255,0,0])
  self.assertEqual(len(record['ancestor_transforms']),2)
  self.assertFalse(record['simulating'])
  self.assertEqual(record['simulationTimeScale'],2)
  self.assertEqual(scene,before)
 def test_particle_scene_cycle_is_bounded(self):
  scene=Element(name='scene',children=[])
  scene.children.append(scene)
  result=module.capture(NS(GetCurrentShot=lambda:Element(name='shot1',scene=scene)),'609')
  self.assertEqual(result['particles'],[])
