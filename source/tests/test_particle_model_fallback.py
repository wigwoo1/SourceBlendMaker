import unittest
from particle_model_fallback import resolve,resolve_lerp

class ModelFallbackTests(unittest.TestCase):
    def definition(self,p=None):
        return {'modules':{'initializers':[{'function':'Position on Model Random','parameters':p or {}}]}}
    def test_unattached_uses_selected_cp_without_mutating_source(self):
        original=self.definition({'control_point_number':1,'direction bias':[2,3,4],'model hitbox scale':2})
        result,used=resolve(original,{'control_points':[{},{}],'control_models':[]})
        self.assertTrue(used)
        self.assertEqual(result['modules']['initializers'][0]['parameters']['Starting Control Point'],1)
        self.assertEqual(original['modules']['initializers'][0]['function'],'Position on Model Random')
    def test_attached_and_missing_cp_rejected(self):
        for descriptor in ({'control_models':[{}],'control_points':[{}]}, {'control_models':[],'control_points':[]}):
            with self.assertRaises(ValueError):resolve(self.definition(),descriptor)
    def test_disabled_operator_preserved(self):
        original=self.definition({'operator enabled':False})
        result,used=resolve(original,{})
        self.assertIs(result,original)
        self.assertFalse(used)
    def test_no_hitbox_movement_exits_without_changes_to_other_operators(self):
        original={'modules':{'operators':[{'function':'Movement Lerp to Hitbox','parameters':{}},
                                         {'function':'Movement Basic','parameters':{}}]}}
        result,used=resolve_lerp(original,{'control_models':[],'control_points':[{}]})
        self.assertTrue(used)
        self.assertEqual([m['function'] for m in result['modules']['operators']],['Movement Basic'])
        self.assertEqual(len(original['modules']['operators']),2)
        with self.assertRaises(ValueError):resolve_lerp(original,{'control_models':[{}],'control_points':[{}]})
