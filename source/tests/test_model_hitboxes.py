import struct,unittest
from model_hitboxes import read

class HitboxTests(unittest.TestCase):
    def fixture(self):
        raw=bytearray(268);raw[:4]=b'IDST'
        struct.pack_into('<i',raw,4,49);struct.pack_into('<i',raw,76,len(raw))
        struct.pack_into('<i',raw,156,2);struct.pack_into('<ii',raw,172,1,180)
        struct.pack_into('<iii',raw,180,80,1,12)
        struct.pack_into('<ii6fi',raw,192,1,3,-1,-2,-3,1,2,3,0)
        raw[260:268]=b'default\0'
        return raw
    def test_relative_offsets_and_bone_local_bounds(self):
        result=read(self.fixture())
        self.assertEqual(result['sets'][0]['name'],'default')
        self.assertEqual(result['sets'][0]['boxes'][0]['minimum'],[-1,-2,-3])
        self.assertEqual(result['sets'][0]['boxes'][0]['bone'],1)
    def test_invalid_layout_ranges_and_bounds_rejected(self):
        for offset,fmt,value in ((4,'i',53),(76,'i',999),(172,'i',-1),(184,'i',-1),(192,'i',9),(200,'f',float('nan')),(200,'f',5)):
            raw=self.fixture();struct.pack_into('<'+fmt,raw,offset,value)
            with self.assertRaises(ValueError):read(raw)
