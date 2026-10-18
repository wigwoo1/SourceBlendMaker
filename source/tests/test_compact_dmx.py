import io,sys,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import datamodel
from compact_dmx import NumericArray

class CompactArrays(unittest.TestCase):
 def test_reader_preserves_numeric_types(self):
  dm=datamodel.DataModel('test',1);root=dm.add_element('root')
  for name,t,values in [('floats',float,[i*.125 for i in range(1100)]),('times',datamodel.Time,[datamodel.Time(i*.01) for i in range(1100)]),('vectors',datamodel.Vector3,[datamodel.Vector3((i,2,3)) for i in range(1100)]),('quats',datamodel.Quaternion,[datamodel.Quaternion((0,0,0,1)) for i in range(1100)])]:root[name]=datamodel.make_array(values,t)
  raw=dm.echo('binary',5)
  normal=datamodel.load(in_file=io.BytesIO(raw)).root;compact=datamodel.load(in_file=io.BytesIO(raw),compact_arrays=True).root
  for name in normal:
   self.assertIsInstance(compact[name],NumericArray)
   self.assertEqual(list(compact[name]),list(normal[name]))
   self.assertEqual(compact[name][-1],normal[name][-1])
   self.assertEqual(compact[name][10:15],normal[name][10:15])
 def test_truncation_rejected(self):
  with self.assertRaises(ValueError):NumericArray(b'123','f',lambda x:x[0])
