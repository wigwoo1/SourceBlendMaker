import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_texture_recovery import payload
class RecoveryTests(unittest.TestCase):
 def texture(self):
  h=bytearray(80);struct.pack_into('<4sIII',h,0,b'VTF\0',7,3,80);return bytes(h)
 def test_original_bytes_unchanged(self):
  data=self.texture();self.assertEqual(payload(data),(data,None))
 def test_material_prefix_is_explicitly_reported(self):
  prefix=b'"UnlitGeneric" { "$basetexture" "dev/null" }\r\n';data=prefix+self.texture();raw,report=payload(data);self.assertEqual(raw,self.texture());self.assertEqual(report['removed_prefix_bytes'],len(prefix));self.assertFalse(report['source_asset_modified'])
 def test_arbitrary_junk_is_not_recovered(self):
  for prefix in (b'junk',b'\x00"UnlitGeneric" {}',b'"UnlitGeneric" {',b' '*4096):
   with self.assertRaises(ValueError):payload(prefix+self.texture())
 def test_embedded_invalid_texture_rejected(self):
  with self.assertRaises(ValueError):payload(b'"UnlitGeneric" {}'+b'VTF\0broken')
