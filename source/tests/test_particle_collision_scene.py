import unittest
from particle_collision_scene import _check_entities,TRACE_CONTENTS_MASK,prepare,required
from types import SimpleNamespace
from particle_brush_trace import PreparedBrushTracer


class CollisionEntityEligibilityTests(unittest.TestCase):
    def test_only_enabled_trace_constraints_request_geometry(self):
        def descriptor(value):return {'definitions':[{'modules':{'constraints':[{'function':'Collision via traces','parameters':{'operator enabled':value}}]}}]}
        self.assertFalse(required([descriptor(False)]));self.assertFalse(required([descriptor(0)]))
        self.assertTrue(required([descriptor(True)]));self.assertFalse(required([{}]))
    def test_map_resolution_rejects_missing_map_and_session_models(self):
        assets=SimpleNamespace(buffer=lambda path:None)
        session=SimpleNamespace(elements={})
        with self.assertRaisesRegex(ValueError,'requires a session map'):prepare(session,SimpleNamespace(map=''),assets)
        with self.assertRaisesRegex(ValueError,'Missing particle collision map: maps/stage.bsp'):
            prepare(session,SimpleNamespace(map='stage'),assets)
        session.elements={'model':SimpleNamespace(type='DmeGameModel')}
        with self.assertRaisesRegex(ValueError,'session models'):
            prepare(session,SimpleNamespace(map='stage'),assets)

    def test_map_resolution_rejects_traversal(self):
        for path in ('../stage.bsp','C:/stage.bsp','maps//stage.bsp'):
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'Invalid'):
                prepare(SimpleNamespace(elements={}),SimpleNamespace(map=path),None)
    def test_installed_query_mask_includes_each_bit_and_excludes_water(self):
        self.assertEqual(TRACE_CONTENTS_MASK,0x0200400B)
        for contents in (1,2,8,0x4000,0x2000000,32):
            brush={'index':0,'contents':contents,'sides':[{'normal':(0,0,1),'distance':0}]}
            hit=PreparedBrushTracer([brush],TRACE_CONTENTS_MASK)((0,0,1),(0,0,-1),0)
            self.assertEqual(hit is not None,contents!=32)
    def test_world_and_non_geometry_entities_allowed(self):
        _check_entities(b'// map\n{"classname" "worldspawn"}\n{"classname" "light" "origin" "0 0 0"}\0')

    def test_dynamic_model_and_brush_entities_rejected(self):
        for entity in (b'{"classname" "prop_dynamic"}',
                       b'{"classname" "misc" "model" "models/test.mdl"}',
                       b'{"classname" "func_brush"}'):
            with self.subTest(entity=entity),self.assertRaisesRegex(ValueError,'map model or brush'):
                _check_entities(entity)

    def test_malformed_entities_fail_closed(self):
        for entity in (b'{"classname" "light"',b'{garbage}',b'{"model"}',b'{}unexpected'):
            with self.subTest(entity=entity),self.assertRaises(ValueError):_check_entities(entity)
