import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from particle_sprite_state import remap_scalars

class ScalarRemapTests(unittest.TestCase):
    def module(self,**values):return {'function':'Remap Initial Scalar','parameters':values}

    def test_birth_time_controls_radius_and_alpha(self):
        fields={8:.25,3:10,7:.8}
        values=remap_scalars(fields,[self.module(**{'input maximum':.5,'output maximum':20}),self.module(**{'input maximum':.5,'output field':7,'output maximum':1})])
        self.assertEqual(values[3],10);self.assertEqual(values[7],.5)
        self.assertEqual(fields[7],.8)

    def test_reversed_interval_multiplies_sampled_range(self):
        module=self.module(**{'input minimum':.6,'input maximum':0,'output minimum':.2,'output maximum':1,'output field':10,'output is scalar of initial random range':True})
        self.assertAlmostEqual(remap_scalars({8:.3,10:2},[module])[10],1.2)

    def test_active_range_and_emitter_lifetime_gate_preserve_other_births(self):
        module=self.module(**{'input maximum':.1,'output field':7,'only active within specified input range':True})
        self.assertEqual(remap_scalars({8:1,7:.8},[module])[7],.8)
        module['parameters'].update({'only active within specified input range':False,'emitter lifetime end time (seconds)':.5})
        self.assertEqual(remap_scalars({8:1,7:.8},[module])[7],.8)

    def test_repeated_remaps_apply_in_pcf_order(self):
        modules=[self.module(**{'output minimum':.5,'output maximum':.5,'output is scalar of initial random range':True}),self.module(**{'output minimum':.2,'output maximum':.2,'output is scalar of initial random range':True})]
        self.assertAlmostEqual(remap_scalars({8:.2,3:100},modules)[3],10)
