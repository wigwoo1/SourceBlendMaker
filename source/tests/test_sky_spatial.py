import unittest,sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sky_spatial import read_leaves

class LeafTests(unittest.TestCase):
    def test_area_flags_and_face_range(self):
        for version,size in ((0,56),(1,32)):
            data=bytearray(size)
            struct.pack_into('<ihH',data,0,0,7,5|(3<<9))
            struct.pack_into('<HH',data,20,19,4)
            leaf=read_leaves(data,version)[0]
            self.assertEqual((leaf.area,leaf.flags,leaf.cluster,leaf.first_face,leaf.face_count),(5,3,7,19,4))
    def test_truncated_and_unknown_formats_rejected(self):
        with self.assertRaises(ValueError):read_leaves(b'partial',1)
        with self.assertRaises(ValueError):read_leaves(b'',2)
