import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from particle_warp import apply_birth, factor, settings, transform_position, transform_vector
from particle_bake import plan


IDENTITY=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
ROT_Z_90=((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.))


class ParticleWarpTests(unittest.TestCase):
    @staticmethod
    def definition(warp_first=False):
        def module(name, parameters=None):return {'function':name,'parameters':parameters or {}}
        initializers=[module('Position Within Sphere Random'),
                      module('Position Modify Offset Random'),
                      module('Position Modify Warp Random',{'warp min':[.2]*3,
                          'warp transition time (treats min/max as start/end sizes)':2.})]
        if warp_first:initializers.reverse()
        return {'parameters':{'initial_particles':0},'modules':{
            'renderers':[module('render_animated_sprites')],
            'emitters':[module('emit_continuously',{'emission_rate':50})],
            'initializers':initializers,'operators':[],'forces':[],'constraints':[]}}

    def test_planner_accepts_installed_warp_initializer(self):
        result=plan(self.definition())
        self.assertEqual(result['rate'],50.)

    def test_planner_rejects_position_writer_after_warp(self):
        with self.assertRaisesRegex(ValueError,'Position warp after'):
            plan(self.definition(warp_first=True))

    def test_planner_accepts_ordered_repeated_spawn_offsets(self):
        definition=self.definition()
        offset={'function':'Position Modify Offset Random','parameters':{
            'offset min':[0.,0.,.5],'offset max':[0.,0.,.5],
            'offset proportional to radius 0/1':True}}
        definition['modules']['initializers'].insert(2,offset)
        self.assertEqual(plan(definition)['rate'],50.)

    def test_engine_defaults_are_unit_warp(self):
        self.assertEqual(factor({}, 4.), (1.,1.,1.))

    def test_transition_interpolates_and_clamps(self):
        parameters={'warp min':[.2,.4,.6], 'warp transition time (treats min/max as start/end sizes)':2.}
        self.assertEqual(factor(parameters,0.),(.2,.4,.6))
        for actual,expected in zip(factor(parameters,1.),(.6,.7,.8)):self.assertAlmostEqual(actual,expected)
        self.assertEqual(factor(parameters,3.),(1.,1.,1.))

    def test_transition_start_and_reverse(self):
        parameters={'warp min':[.2]*3,'warp max':[.8]*3,
                    'warp transition time (treats min/max as start/end sizes)':2.,
                    'warp transition start time':3.,'reverse':True}
        self.assertEqual(factor(parameters,3.),(.8,.8,.8))
        for actual in factor(parameters,5.):self.assertAlmostEqual(actual,.2)

    def test_random_bounds_use_supplied_axis_values(self):
        p={'warp min':[0.,1.,2.],'warp max':[1.,3.,6.]}
        self.assertEqual(factor(p,0.,(0.,.5,1.)),(0.,2.,6.))

    def test_local_scale_respects_control_point_rotation_and_origin(self):
        self.assertEqual(transform_position((0.,12.,0.),(0.,10.,0.),ROT_Z_90,(2.,1.,1.)),(0.,14.,0.))
        self.assertEqual(transform_vector((0.,2.,0.),ROT_Z_90,(2.,1.,1.)),(0.,4.,0.))

    def test_birth_warps_position_offset_and_velocity_in_order(self):
        modules=[{'function':'Position Modify Warp Random','parameters':{
            'warp min':[2.,1.,1.], 'warp max':[2.,1.,1.], 'control_point_number':0,
            'warp transition time (treats min/max as start/end sizes)':1.}}]
        position,offset,velocity=apply_birth((3.,1.,0.),(0.,2.,0.),(1.,0.,0.),modules,.5,
            lambda cp:((1.,1.,0.),IDENTITY),None)
        self.assertEqual(position,(5.,1.,0.))
        self.assertEqual(offset,(0.,2.,0.))
        self.assertEqual(velocity,(2.,0.,0.))

    def test_invalid_parameters_fail_closed(self):
        for p in ({'warp min':[1.,2.]}, {'warp transition time (treats min/max as start/end sizes)':float('nan')},
                   {'control_point_number':64}):
            with self.assertRaises(ValueError):settings(p)


if __name__=='__main__':
    unittest.main()
