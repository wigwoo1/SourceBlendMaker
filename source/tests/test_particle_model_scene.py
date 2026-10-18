import copy,unittest
from particle_model_scene import prepare_definition

def fixture():
    return dict(modules={
        'initializers':[dict(function='Position on Model Random',parameters={}),dict(function='Lifetime Random',parameters={})],
        'operators':[dict(function='Movement Lerp to Hitbox',parameters={})],
        'forces':[],'constraints':[],'emitters':[],
        'renderers':[dict(function='render_animated_sprites',parameters={})]})

class ModelSceneTests(unittest.TestCase):
    def test_offset_preserves_authored_parameters_and_order(self):
        graph=fixture()
        module=dict(function='Position Modify Offset Random',parameters={'offset min':[-2,-3,-4],'offset max':[2,3,4]})
        graph['modules']['initializers'].insert(0,module)
        original=copy.deepcopy(graph)
        prepared,_=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertEqual(graph,original)
        self.assertEqual(prepared['modules']['initializers'][0],module)
    def test_secondary_alpha_retained_without_mutating_model_graph(self):
        graph=fixture()
        graph['modules']['operators'].append(dict(function='Oscillate Scalar Simple',parameters={'oscillation field':16,'oscillation rate':-250,'oscillation frequency':8}))
        original=copy.deepcopy(graph)
        prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertEqual(graph,original)
        self.assertEqual(prepared['modules']['operators'],[original['modules']['operators'][-1]])
    def test_other_simple_fields_and_timed_secondary_rejected(self):
        for p in ({'oscillation field':7},{'oscillation field':3},{'oscillation field':16,'operator end fadein':1}):
            graph=fixture()
            graph['modules']['operators'].append(dict(function='Oscillate Scalar Simple',parameters=p))
            with self.assertRaises(ValueError):prepare_definition(graph,{'control_models':[{'id':'model'}]})
    def test_velocity_lerp_requires_movement_and_preserves_initializer_order(self):
        for name in ('Velocity Random','Velocity Noise'):
            graph=fixture()
            graph['modules']['initializers'].insert(0,dict(function=name,parameters={}))
            with self.assertRaises(ValueError):
                prepare_definition(graph,{'control_models':[{'id':'model'}]})
            graph['modules']['operators'].insert(0,dict(function='Movement Basic',parameters={}))
            original=copy.deepcopy(graph)
            prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
            self.assertEqual(graph,original)
            self.assertEqual(prepared['modules']['initializers'][0]['function'],name)
            self.assertEqual([m['function'] for m in settings['motion']],['Movement Basic','Movement Lerp to Hitbox'])
    def test_lerp_with_movement_uses_authored_ordered_history(self):
        graph=fixture();graph['modules']['operators'].insert(0,dict(function='Movement Basic',parameters={}))
        prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertEqual([m['function'] for m in settings['motion']],['Movement Basic','Movement Lerp to Hitbox'])
    def test_bone_lock_velocity_after_placement_retained(self):
        graph=fixture();graph['modules']['operators']=[dict(function='Movement Lock to Bone',parameters={})]
        graph['modules']['initializers'].append(dict(function='Velocity Random',parameters={}))
        prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertEqual(prepared['modules']['initializers'][-1]['function'],'Velocity Random')
        graph['modules']['initializers'].insert(0,graph['modules']['initializers'].pop())
        prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertEqual(prepared['modules']['initializers'][0]['function'],'Velocity Random')
    def test_bone_lock_extracts_ordered_motion_and_preserves_input(self):
        graph=fixture()
        graph['modules']['operators']=[dict(function='Movement Basic',parameters={'gravity':[0,0,50]}),dict(function='Movement Lock to Bone',parameters={})]
        saved=copy.deepcopy(graph)
        prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertEqual(graph,saved)
        self.assertEqual([m['function'] for m in settings['motion']],['Movement Basic','Movement Lock to Bone'])
        self.assertEqual([m['function'] for m in prepared['modules']['operators']],['Movement Basic'])
    def test_invalid_bone_lock_flags_and_jump_threshold_rejected(self):
        for parameters in ({'rigid lock':'false'},{'instant jump threshold':-1},{'instant jump threshold':float('nan')}):
            graph=fixture();graph['modules']['operators']=[dict(function='Movement Lock to Bone',parameters=parameters)]
            with self.assertRaises(ValueError):prepare_definition(graph,{'control_models':[{'id':'model'}]})
    def test_basic_movement_after_model_spawn_is_retained_without_follow(self):
        graph=fixture();graph['modules']['operators']=[dict(function='Movement Basic',parameters={'gravity':[0,0,-50],'drag':0})]
        prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertIsNone(settings['follow'])
        self.assertEqual(prepared['modules']['operators'],graph['modules']['operators'])
    def test_preserves_original_and_extracts_follow(self):
        original=fixture();saved=copy.deepcopy(original)
        result,settings=prepare_definition(original,{'control_models':[{'id':'model'}]})
        self.assertEqual(original,saved)
        self.assertEqual(result['modules']['initializers'][0]['function'],'Position From Control Points')
        self.assertEqual(settings['control_point'],0)
        self.assertEqual(result['modules']['operators'],[])
    def test_rejects_additional_motion_and_mismatched_target(self):
        for extra in ('Movement Lock to Control Point','Oscillate Vector'):
            graph=fixture();graph['modules']['operators'].append(dict(function=extra,parameters={}))
            with self.assertRaises(ValueError):prepare_definition(graph,{'control_models':[{'id':'model'}]})
        graph=fixture();graph['modules']['operators'][0]['parameters']['control point number']=1
        with self.assertRaises(ValueError):prepare_definition(graph,{'control_models':[{'id':'model'},{'id':'other'}]})
    def test_rejects_shared_strength_and_invalid_placement(self):
        for key,value in (('model hitbox scale',-.5),('operator time scale min',2),('direction bias',[float('nan'),0,0])):
            graph=fixture();graph['modules']['initializers'][0]['parameters'][key]=value
            with self.assertRaises(ValueError):prepare_definition(graph,{'control_models':[{'id':'model'}]})
    def test_records_sfm_query_ignored_authored_settings(self):
        graph=fixture();graph['modules']['initializers'][0]['parameters'].update({'direction bias':[0,0,100],'force to be inside model':1})
        prepared,settings=prepare_definition(graph,{'control_models':[{'id':'model'}]})
        self.assertEqual(settings['sfm_query_ignored_settings'],{'direction bias':[0,0,100],'force to be inside model':1})
