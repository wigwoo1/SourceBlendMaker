import unittest,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_noise_emitter import births,rate
from particle_sim import Segment
tables=[t['values'] for t in json.loads(Path(__file__).resolve().parents[1].joinpath('particle_noise_tables.json').read_text())['tables']]

class BirthTests(unittest.TestCase):
 def test_constant_count(self):
  result=births({},[Segment(0,1)],tables,rate_function=lambda _:20)
  self.assertEqual(len(result),20)
  self.assertTrue(all(0<b.time<=1 for b in result))
 def test_emission_window(self):
  result=births({'emission_start_time':.2,'emission_duration':.3},[Segment(0,1)],tables,rate_function=lambda _:100)
  self.assertEqual(len(result),30)
  self.assertTrue(all(.2<b.time<=.5 for b in result))
 def test_paused_gate(self):
  segments=[Segment(0,.5),Segment(.5,1,False,False),Segment(1,1.5)]
  result=births({},segments,tables,rate_function=lambda _:20)
  self.assertEqual(len(result),20)
  self.assertFalse(any(.5<b.time<=1 for b in result))
 def test_authored_rate_varies(self):
  parameters={'emission minimum':5,'emission maximum':50,'time noise coordinate scale':1000}
  samples=[rate(parameters,i/120,tables) for i in range(100)]
  self.assertTrue(all(5<=v<=50 for v in samples))
  self.assertGreater(max(samples)-min(samples),10)
 def test_scaled_noise_rejected(self):
  for key in ('world time noise coordinate scale','scale emission to used control points'):
   with self.assertRaises(ValueError):rate({key:1},0,tables)
 def test_capacity_limit(self):
  with self.assertRaises(ValueError):births({},[Segment(0,1)],tables,max_particles=2,rate_function=lambda _:20)

if __name__=='__main__':unittest.main()
