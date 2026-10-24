import struct
import unittest
from bsp_collision import read_model_brushes
from particle_brush_entities import resolve
from particle_collision_scene import world_provider


def fixture(entity='{"classname" "func_brush" "model" "*1" "origin" "0 0 10" "spawnflags" "2"}'):
    raw=bytearray(1036);raw[:4]=b'VBSP';struct.pack_into('<i',raw,4,20)
    # Model zero is empty. Model one is the local box [-1,1]^3.
    planes=[(1,0,0,1,0),(-1,0,0,1,0),(0,1,0,1,1),(0,-1,0,1,1),(0,0,1,1,2),(0,0,-1,1,2)]
    leaves=bytearray(64);struct.pack_into('<2H',leaves,32+24,0,1)
    payloads={0:(entity.encode()+b'\0',0),1:(b''.join(struct.pack('<4fi',*p) for p in planes),0),
              14:(struct.pack('<9f3i',*([0.]*9),-1,0,0)+struct.pack('<9f3i',*([0.]*9),-2,0,0),0),
              10:(leaves,1),17:(struct.pack('<H',0),0),18:(struct.pack('<iii',0,6,1),0),
              19:(b''.join(struct.pack('<Hhhh',i,-1,-1,0) for i in range(6)),0)}
    for index,(payload,version) in payloads.items():
        struct.pack_into('<4i',raw,8+16*index,len(raw),len(payload),version,0);raw.extend(payload)
    return raw


class StaticBrushEntitiesTests(unittest.TestCase):
    def test_submodel_leaf_selection_is_independent_of_world(self):
        raw=fixture()
        self.assertEqual(read_model_brushes(raw,0)['brushes'],[])
        self.assertEqual(len(read_model_brushes(raw,1)['brushes']),1)
        with self.assertRaisesRegex(ValueError,'model index'):read_model_brushes(raw,2)

    def test_real_provider_translates_planes_and_retains_radius(self):
        tracer,report=world_provider(fixture(),0)
        self.assertEqual(report['entity_brush_count'],1)
        self.assertAlmostEqual(tracer((0,0,20),(0,0,0),0)['fraction'],.45)
        self.assertAlmostEqual(tracer((0,0,20),(0,0,0),1)['fraction'],.4)
        self.assertIsNone(tracer((3,0,20),(3,0,0),0))
        self.assertTrue(tracer((0,0,10),(0,0,10),0)['start_solid'])
        self.assertIs(tracer.for_settings({'brush only':False}),tracer)
        with self.assertRaisesRegex(ValueError,'Brush-only'):tracer.for_settings({'brush only':True})

    def test_never_solid_and_disabled_toggle_do_not_collide(self):
        for fields in ('"Solidity" "1"','"Solidity" "0" "StartDisabled" "1"'):
            tracer,report=world_provider(fixture('{"classname" "func_brush" "model" "*1" '+fields+'}'),0)
            self.assertIsNone(tracer((0,0,10),(0,0,-10),0))
            self.assertFalse(report['static_brush_entities'][0]['solid'])

    def test_always_solid_even_when_hidden(self):
        tracer,_=world_provider(fixture('{"classname" "func_brush" "model" "*1" "Solidity" "2" "StartDisabled" "1"}'),0)
        self.assertIsNotNone(tracer((0,0,10),(0,0,-10),0))

    def test_unresolved_or_dynamic_geometry_still_rejected(self):
        for extra in ('"targetname" "door"','"parentname" "moving"','"angles" "0 90 0"',
                      '"spawnflags" "1"','"origin" "nan 0 0"','"excludednpc" "npc_test"'):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                world_provider(fixture('{"classname" "func_brush" "model" "*1" '+extra+'}'),0)
        with self.assertRaisesRegex(ValueError,'Unresolved'):world_provider(fixture('{}'),0)
        with self.assertRaisesRegex(ValueError,'session models'):world_provider(fixture(),1)

    def test_no_mutation_or_double_translation(self):
        raw=fixture();entity={'classname':'func_brush','model':'*1','origin':'0 0 10'}
        a,_=resolve(raw,[entity],2);b,_=resolve(raw,[entity],2)
        self.assertEqual(a,b)
        self.assertEqual(read_model_brushes(raw,1)['brushes'][0]['sides'][4]['distance'],1.)
