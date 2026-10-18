import struct,unittest
from bsp_collision import read_brushes,read_world_brushes

class BrushCollisionTests(unittest.TestCase):
    def fixture(self):
        raw=bytearray(1036);raw[:4]=b'VBSP';struct.pack_into('<i',raw,4,20)
        for index,payload in ((1,struct.pack('<4fi',0,0,1,8,2)),(19,struct.pack('<Hhhh',0,-1,-1,1)),(18,struct.pack('<iii',0,1,1))):
            struct.pack_into('<4i',raw,8+16*index,len(raw),len(payload),0,0);raw.extend(payload)
        return raw
    def test_planes_contents_and_bevel_retained(self):
        result=read_brushes(self.fixture());brush=result['brushes'][0]
        self.assertEqual(brush['contents'],1)
        self.assertEqual(brush['sides'][0]['normal'],(0,0,1))
        self.assertEqual(brush['sides'][0]['distance'],8)
        self.assertTrue(brush['sides'][0]['bevel'])
    def test_truncated_and_bad_index_rejected(self):
        raw=self.fixture()
        with self.assertRaises(ValueError):read_brushes(raw[:-1])
        offset=struct.unpack_from('<i',raw,8+16*19)[0];struct.pack_into('<H',raw,offset,2)
        with self.assertRaises(ValueError):read_brushes(raw)
    def test_compressed_lump_rejected_explicitly(self):
        raw=self.fixture();struct.pack_into('<i',raw,8+16*18+12,100)
        with self.assertRaisesRegex(ValueError,'Compressed'):read_brushes(raw)
    def test_world_leaf_references_exclude_unreferenced_submodel_brush(self):
        raw=self.fixture()
        # Replace brush lump with two copies; only brush zero belongs to world.
        leaf=bytearray(32);struct.pack_into('<2H',leaf,24,0,1)
        for index,payload,version in ((18,struct.pack('<iii',0,1,1)*2,0),
              (14,struct.pack('<9f3i',*([0.]*9),-1,0,0),0),
              (10,leaf,1),(17,struct.pack('<H',0),0)):
            struct.pack_into('<4i',raw,8+16*index,len(raw),len(payload),version,0);raw.extend(payload)
        result=read_world_brushes(raw)
        self.assertEqual(result['all_brush_count'],2)
        self.assertEqual([b['index'] for b in result['brushes']],[0])
